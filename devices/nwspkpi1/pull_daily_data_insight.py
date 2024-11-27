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
        
        # Extract the desktop image
        article_block = first_insight.find('figure', {'class': 'article-block__image'})
        if not article_block:
            raise Exception("Could not find article image block")
            
        picture = article_block.find('picture')
        if not picture:
            raise Exception("Could not find picture element in article block")
            
        # Find desktop source
        sources = picture.find_all('source')
        desktop_source = None
        for source in sources:
            if 'srcset' in source.attrs:
                srcset = source['srcset']
                if 'desktop' in srcset:
                    desktop_source = source
                    break
        
        if not desktop_source:
            raise Exception("Could not find desktop source in article block")
        
        # Get the highest resolution desktop image
        srcset = desktop_source['srcset']
        # Split by comma and clean up
        urls = [u.strip() for u in srcset.split(',')]
        # Find the URL with the highest width number
        highest_res_url = None
        highest_width = 0
        for url in urls:
            parts = url.split(' ')
            if len(parts) >= 2 and parts[1].endswith('w'):
                width = int(parts[1][:-1])  # Remove 'w' and convert to int
                if width > highest_width:
                    highest_width = width
                    highest_res_url = parts[0]
        
        if not highest_res_url:
            raise Exception("Could not find valid image URL")
            
        # Add the base URL if it starts with /
        if highest_res_url.startswith('/'):
            highest_res_url = f"https://ourworldindata.org{highest_res_url}"
        
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
            f'<img src="{highest_res_url}"',
            html_content
        )

        # Write the updated HTML file
        with open(html_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print(f"\nSuccessfully updated daily insight at {html_path}")
        print(f"Date: {current_date}")
        print(f"Title: {title}")
        print(f"Image URL: {highest_res_url}")
        
    except requests.RequestException as e:
        print(f"Error fetching the page: {str(e)}")
    except Exception as e:
        print(f"Error updating insight: {str(e)}")
        raise  # This will show the full error traceback

if __name__ == "__main__":
    update_insight()