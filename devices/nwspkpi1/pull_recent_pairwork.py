import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from pyairtable import Api
import anthropic
from datetime import datetime

# Load environment variables
load_dotenv()
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Constants
CSS_STYLES = """
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    background: #1a1a1a;
    font-family: monospace;
    padding: 20px;
    margin: 0;
    min-height: 100vh;
    max-width: 100vw;
    overflow-x: hidden;
}

h1 {
    color: #CDC5B4;
    font-size: 24px;
    margin-bottom: 20px;
    padding: 10px;
    border-bottom: 2px solid #4C7363;
    font-family: "Courier New", monospace;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    width: 100%;
    margin: 0 auto;
}

.summary p {
    background: linear-gradient(45deg, #2a2522 0%, #33302d 100%);
    border: 1px solid #4C7363;
    padding: 20px;
    color: #CDC5B4;
    position: relative;
    overflow: hidden;
    box-shadow: 3px 3px 0 #4C7363;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.summary p::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 30px;
    background: #4C7363;
    opacity: 0.3;
}

.summary strong {
    display: block;
    font-size: 14px;
    color: #B5A642;
    margin-bottom: 15px;
    font-family: "Courier New", monospace;
    border-bottom: 1px solid #4C7363;
    padding-bottom: 5px;
    position: relative;
    z-index: 1;
}

.summary span {
    display: block;
    padding-left: 15px;
    position: relative;
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.5;
}

.summary span::before {
    content: ">";
    position: absolute;
    left: 0;
    color: #4C7363;
}

.timestamp {
    margin-top: 20px;
    text-align: right;
    font-size: 12px;
    font-family: "Courier New", monospace;
    color: #4C7363;
}
"""

# Define the HTML template with a style placeholder
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recent Pair Work Summary</title>
    <style>
    {styles}
    </style>
</head>
<body>
    <h1>Recent Pair Work Summary</h1>
    <div class="summary">
        {summary}
    </div>
    <div class="timestamp">
        Last updated: {timestamp}
    </div>
</body>
</html>"""

# Modify the update_html_file function to use both templates
def update_html_file(summary):
    """Update the HTML file with the new summary."""
    try:
        current_dir = Path(__file__).parent
        html_path = current_dir / 'display_rotation' / 'pages' / 'pairwork.html'
        
        # Generate HTML content with both templates
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = HTML_TEMPLATE.format(
            styles=CSS_STYLES,
            summary=summary,
            timestamp=timestamp
        )
        
        # Create directories if they don't exist
        html_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"Successfully updated {html_path}")
    except Exception as e:
        print(f"Error updating HTML file: {e}")
        import traceback
        print(traceback.format_exc())

def fetch_recent_records():
    """Fetch the 6 most recent records from Airtable."""
    try:
        api = Api(AIRTABLE_API_KEY)
        table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
        records = table.all(sort=['-Date/Time'], max_records=6)
        return records
    except Exception as e:
        print(f"Error fetching Airtable records: {e}")
        return []

def format_date(date_string):
    """Convert ISO date string to YYYY-MM-DD format."""
    try:
        date_obj = datetime.strptime(date_string.split('T')[0], '%Y-%m-%d')
        return date_obj.strftime('%Y-%m-%d')
    except Exception:
        return date_string

def get_summary_from_llm(notes):
    """Get a summary of the notes from Claude using the Messages API."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": f"Summarize the outcomes of these meetings in 1-3 clear and concise bullet points, maxmimum 50 words. Return only a bulleted list with no other preamble: {notes}"
            }]
        )
        # Get text directly from the first content block
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return "No summary available"
    except Exception as e:
        print(f"Error getting LLM summary: {e}")
        return notes  # Return original notes if LLM fails


def generate_summary(records):
    """Generate a summary of the records."""
    if not records:
        return "No recent records found."
    
    summary = ""
    for record in records:
        fields = record['fields']
        date_str = format_date(fields.get('Date/Time', 'Unknown date'))
        person1 = fields.get('Person 1', '')
        person2 = fields.get('Person 2', '')
        notes = fields.get('Your Notes', '')
        
        # Get summarized notes from LLM
        summarized_notes = get_summary_from_llm(notes)
        
        # Split the summarized notes by bullet points and format them
        bullet_points = [point.strip() for point in summarized_notes.split('\n-') if point.strip()]
        formatted_bullets = '\n'.join([f'<span>{point}</span>' for point in bullet_points])
        
        summary += f"""<p><strong>{date_str} {person1} & {person2}</strong>{formatted_bullets}</p>"""
    
    return summary

def main():
    """Main function to orchestrate the update process."""
    # Fetch recent records
    records = fetch_recent_records()
    if not records:
        print("No records found or error occurred.")
        return
    
    # Generate summary
    summary = generate_summary(records)
    
    # Update HTML file
    update_html_file(summary)

if __name__ == "__main__":
    main()