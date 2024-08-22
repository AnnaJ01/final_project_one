import re
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, TimeoutException

# Configure paths
CHROME_DRIVER_PATH = 'chromedriver'  # Adjust path if necessary

def login_to_wordpress(driver, username, password):
    driver.get("https://wp.thecollector.com/wp-login.php")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'user_login'))).send_keys(username)
    driver.find_element(By.ID, 'user_pass').send_keys(password)
    driver.find_element(By.ID, 'wp-submit').click()
    WebDriverWait(driver, 10).until(EC.title_contains("Dashboard"))

def navigate_to_media_library(driver):
    driver.get("https://wp.thecollector.com/wp-admin/upload.php?mode=list")
    time.sleep(5)
    WebDriverWait(driver, 10).until(EC.title_contains("Media Library"))

def select_images(driver, num_images):
    checkboxes = driver.find_elements(By.XPATH, '//input[@type="checkbox" and contains(@name, "media[]")]')
    if len(checkboxes) < num_images:
        num_images = len(checkboxes)
    for i in range(num_images):
        if not checkboxes[i].is_selected():
            checkboxes[i].click()

def attach_first_selected_image(driver):
    try:
        first_attach_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '(//a[contains(@aria-label, "Attach") and contains(@class, "hide-if-no-js")])[1]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", first_attach_button)
        time.sleep(1)
        first_attach_button.click()
    except ElementClickInterceptedException as e:
        st.error(f"ElementClickInterceptedException encountered: {e}")

def search_and_select_article(driver, article_name):
    try:
        search_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "find-posts-input")))
        search_input.send_keys(article_name)
        search_button = driver.find_element(By.ID, "find-posts-search")
        search_button.click()
        time.sleep(2)
        first_article_radio = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//input[@type="radio" and @name="found_post_id"]'))
        )
        first_article_radio.click()
        select_button = driver.find_element(By.ID, "find-posts-submit")
        select_button.click()
    except TimeoutException:
        st.error(f"Timeout while searching/selecting the article '{article_name}'")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

def extract_image_details(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'poststuff')))
    permalink = driver.find_element(By.ID, 'sample-permalink').get_attribute('href')
    attachment_id = permalink.split('attachment_id=')[1]
    dimensions_text = driver.find_element(By.CSS_SELECTOR, '.misc-pub-dimensions strong').text
    width, height = dimensions_text.replace('×', 'x').split('x')
    name = driver.find_element(By.ID, 'title').get_attribute('value')
    caption = driver.find_element(By.ID, 'attachment_caption').text
    url = driver.find_element(By.ID, 'attachment_url').get_attribute('value')
    details = {
        'id': attachment_id,
        'width': width.strip(),
        'height': height.strip(),
        'name': name,
        'caption': caption.strip(),
        'url': url.strip()
    }
    return details

def generate_caption(id, width, height, name, caption, url):
    return (
        f'[caption id="attachment_{id}" align="aligncenter" width="{width}"]'
        f'<img class="size-full wp-image-{id}" src="{url}" alt="{name.replace("-", " ")}" width="{width}" height="{height}" /> '
        f'{caption}[/caption]'
    )

def process_images(driver, num_images_to_process):
    image_htmls = []
    image_details_list = []
    for i in range(1, num_images_to_process + 1):
        image = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'tbody#the-list tr:nth-child({i}) a'))
        )
        image.click()
        image_details = extract_image_details(driver)
        image_details_list.append(image_details)
        driver.back()
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, 'the-list'))
        )
    for details in image_details_list:
        caption_html = generate_caption(details['id'], details['width'], details['height'], details['name'], details['caption'], details['url'])
        image_htmls.append(caption_html)
    return image_htmls

def replace_br_with_nbsp(html):
    return re.sub(r'<br\s*/?>', '&nbsp;', html, flags=re.IGNORECASE)

def replace_text_with_html(text, image_htmls):
    patterns_used = []
    images_without_captions = []
    for image_html in image_htmls:
        description_match = re.search(r'<img[^>]+> (\w.*?)\[/caption\]', image_html, re.DOTALL)
        if description_match:
            description_text = description_match.group(1).strip()
            pattern = make_pattern(description_text)
            patterns_used.append(pattern)
            text = re.sub(pattern, image_html, text, flags=re.IGNORECASE | re.DOTALL)
        else:
            no_caption_match = re.search(r'<img[^>]+>', image_html)
            if no_caption_match:
                images_without_captions.append(image_html)
    images_without_captions = list(set(images_without_captions))
    for img in reversed(images_without_captions):
        text = img + '\n\n' + text
    return text, patterns_used

def make_pattern(description_text):
    words = re.split(r'\s+', description_text)
    def escape_word(word):
        return re.escape(word) + r'(\s*<[^>]+>\s*)?'
    pattern = r'\s*'.join(escape_word(word) for word in words)
    return pattern

def main():
    st.title("HTML Content Processor")
    
    uploaded_file = st.file_uploader("Upload your HTML file", type=["html"])
    if uploaded_file:
        html_content = uploaded_file.read().decode("utf-8")
        st.write("Original HTML content:")
        st.code(html_content)
        
        st.header("Process HTML")
        article_name = st.text_input("Enter the article name to search and attach:")
        num_images_to_process = st.number_input("Enter the number of images to process:", min_value=1, max_value=20, value=5)

        if st.button("Process"):
            st.write("Processing...")

            # Perform HTML processing
            titles = extract_h2_titles(html_content)
            st.write("Extracted H2 Titles:")
            st.write(titles)
            
            html_content = re.sub(r'<span style="font-weight: 400;">(.*?)<\/span>', r'\1', html_content, flags=re.DOTALL)
            html_content = re.sub(r'<span style="font-weight: 400;"><\/span>', '', html_content)
            html_content = replace_nbsp_with_br(html_content)

            base_domain = 'https://www.thecollector.com/'
            html_content = add_target_blank_to_anchors(html_content, base_domain)
            html_content = ensure_strong_in_h2(html_content)
            html_content = ensure_strong_in_h3(html_content)
            html_content = replace_list_with_numbered_h2(html_content)
            html_content = replace_list_with_numbered_h3(html_content)
            html_content = replace_br_with_nbsp(html_content)

            st.write("Processed HTML content:")
            st.code(html_content)

            # Selenium setup
            service = Service(CHROME_DRIVER_PATH)
            options = Options()
            driver = webdriver.Chrome(service=service, options=options)
            
            try:
                login_to_wordpress(driver, st.text_input("Enter your WordPress username:"), st.text_input("Enter your WordPress password:"))
                navigate_to_media_library(driver)
                select_images(driver, num_images_to_process)
                attach_first_selected_image(driver)
                search_and_select_article(driver, article_name)
                image_htmls = process_images(driver, num_images_to_process)

                result_text, _ = replace_text_with_html(html_content, image_htmls)
                result_text = replace_br_with_nbsp(result_text)

                st.write("Final HTML with images:")
                st.code(result_text)
            finally:
                driver.quit()
                
if __name__ == "__main__":
    main()
