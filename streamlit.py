import streamlit as st
from bs4 import BeautifulSoup
import re
import pyperclip
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import time

# Streamlit application
st.title("HTML Content Processor and Image Manager")

# Input for article name and number of images
article_name_to_search = st.text_input("Enter the article name to search and attach:")
num_images_to_process = st.number_input("Enter the number of images to process:", min_value=1, step=1)

# Text area for pasted HTML
pasted_text = st.text_area("Paste HTML content here:")

def extract_h2_titles(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    h2_tags = soup.find_all('h2')
    titles = [tag.get_text(strip=True) for tag in h2_tags]
    return titles

if st.button('Process HTML'):
    # Extract titles
    titles = extract_h2_titles(pasted_text)
    st.write("Extracted Titles:", titles)

    # Removing spans
    pattern_with_content = r'<span style="font-weight: 400;">(.*?)<\/span>'
    pasted_text = re.sub(pattern_with_content, r'\1', pasted_text, flags=re.DOTALL)
    pattern_empty = r'<span style="font-weight: 400;"><\/span>'
    pasted_text = re.sub(pattern_empty, '', pasted_text)

    # Replace &nbsp; with <br>
    def replace_nbsp_with_br(html):
        return re.sub(r'&nbsp;', '<br>', html)

    pasted_text = replace_nbsp_with_br(pasted_text)

    # Open anchor tags in new window
    def add_target_blank_to_anchors(html, base_domain):
        soup = BeautifulSoup(html, 'html.parser')
        anchors = soup.find_all('a', href=True)
        for a in anchors:
            href = a['href']
            if not href.startswith(base_domain):
                a['target'] = '_blank'
                a['rel'] = 'noopener'
        return str(soup)

    base_domain = 'https://www.thecollector.com/'
    pasted_text = add_target_blank_to_anchors(pasted_text, base_domain)

    # Ensure <h2> tags are bold
    def ensure_strong_in_h2(html):
        soup = BeautifulSoup(html, 'html.parser')
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            if h2.find('b'):
                for b in h2.find_all('b'):
                    strong_tag = soup.new_tag('strong')
                    strong_tag.extend(b.contents)
                    b.replace_with(strong_tag)
            if not h2.find('strong'):
                strong_tag = soup.new_tag('strong')
                strong_tag.extend(h2.contents)
                h2.clear()
                h2.append(strong_tag)
        return str(soup)

    pasted_text = ensure_strong_in_h2(pasted_text)

    # Ensure <h3> tags are bold
    def ensure_strong_in_h3(html):
        soup = BeautifulSoup(html, 'html.parser')
        h3_tags = soup.find_all('h3')
        for h3 in h3_tags:
            if h3.find('b'):
                for b in h3.find_all('b'):
                    strong_tag = soup.new_tag('strong')
                    strong_tag.extend(b.contents)
                    b.replace_with(strong_tag)
            if not h3.find('strong'):
                strong_tag = soup.new_tag('strong')
                strong_tag.extend(h3.contents)
                h3.clear()
                h3.append(strong_tag)
        return str(soup)

    pasted_text = ensure_strong_in_h3(pasted_text)

    # Replace list with numbered h2
    def replace_list_with_numbered_h2(html):
        soup = BeautifulSoup(html, 'html.parser')
        counter = 1
        for list_tag in soup.find_all(['ul', 'ol']):
            for li in list_tag.find_all('li', attrs={'aria-level': '1'}):
                h2_tag = li.find('h2')
                if h2_tag:
                    strong_tag = h2_tag.find('strong')
                    if strong_tag:
                        new_string = soup.new_string(f"{counter}. ")
                        strong_tag.insert(0, new_string)
                    counter += 1
                    li.replace_with(h2_tag)
            list_tag.unwrap()
        return str(soup)

    pasted_text = replace_list_with_numbered_h2(pasted_text)

    # Replace list with numbered h3
    def replace_list_with_numbered_h3(html):
        soup = BeautifulSoup(html, 'html.parser')
        counter = 1
        list_items = soup.find_all('li', attrs={'aria-level': '1'})
        for li in list_items:
            h3_tag = li.find('h3')
            if h3_tag:
                for b_tag in h3_tag.find_all('b'):
                    strong_tag = soup.new_tag('strong')
                    strong_tag.extend(b_tag.contents)
                    b_tag.replace_with(strong_tag)
                strong_tag = h3_tag.find('strong')
                if strong_tag:
                    new_string = soup.new_string(f"{counter}. ")
                    strong_tag.insert(0, new_string)
                counter += 1
                li.replace_with(h3_tag)
        return str(soup)

    pasted_text = replace_list_with_numbered_h3(pasted_text)

    # Replace <br> with &nbsp;
    def replace_br_with_nbsp(html):
        return re.sub(r'<br\s*/?>', '&nbsp;', html, flags=re.IGNORECASE)

    final_html = replace_br_with_nbsp(pasted_text)
    st.write("Processed HTML Content:")
    st.text_area("Processed HTML", final_html, height=400)

    # Display generated HTML in clipboard
    pyperclip.copy(final_html)
    st.success("Processed text copied to clipboard!")

    # Handling image attachments (simplified, consider running in a separate script)
    st.write("Image Attachment Functionality is under development. To be included in future versions.")

