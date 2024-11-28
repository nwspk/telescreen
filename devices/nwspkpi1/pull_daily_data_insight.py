import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

def update_insight():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, 'display_rotation', 'pages', 'daily_data_insight.html')
    
    try:
        # Fetch the page
        url = 'https://ourworldindata.org/data-insights'
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get the most recent insight
        first_insight = soup.find('div', {'id': 'most-recent-data-insight'})
        if not first_insight:
            raise Exception("Could not find most recent insight")
        
        # Extract the title
        title_elem = first_insight.find('h1', {'class': 'display-3-semibold'})
        if not title_elem:
            raise Exception("Could not find title")
        title = title_elem.text.strip()
        
        # Extract the image
        article_block = first_insight.find('figure', {'class': 'article-block__image'})
        if not article_block:
            raise Exception("Could not find article image block")
            
        # Find the img element directly
        img = article_block.find('img', class_='lightbox-image')
        if not img:
            raise Exception("Could not find image element")
        
        # Get the image source
        img_src = img.get('src')
        if not img_src:
            raise Exception("Could not find image source")
            
        # Add the base URL if it starts with /
        if img_src.startswith('/'):
            img_src = f"https://ourworldindata.org{img_src}"
        
        # Get current date
        current_date = datetime.now().strftime('%B %d, %Y')

        # Read the existing HTML file
        with open(html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Update the dynamic content
        html_content = re.sub(
            r'<div class="date">[^<]*</div>',
            f'<div class="date">{current_date}</div>',
            html_content
        )
        html_content = re.sub(
            r'<h1>[^<]*</h1>',
            f'<h1>{title}</h1>',
            html_content
        )
        html_content = re.sub(
            r'<img src="[^"]*"',
            f'<img src="{img_src}"',
            html_content
        )

        # Write the updated HTML file
        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print(f"\nSuccessfully updated daily insight at {html_path}")
        print(f"Date: {current_date}")
        print(f"Title: {title}")
        print(f"Image URL: {img_src}")
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {str(e)}")
    except Exception as e:
        print(f"Error updating insight: {str(e)}")
        raise  # This will show the full error traceback

if __name__ == "__main__":
    update_insight()