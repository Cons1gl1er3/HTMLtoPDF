import os
import requests
from flask import Flask, request, render_template_string, Response

app = Flask(__name__)

# TODO: Add your PDFShift API key here.
# You can get a key from https://pdfshift.io/
PDFSHIFT_API_KEY = os.environ.get('PDFSHIFT_API_KEY', 'sk_b916102a81dced002bbf6f0cf682041e4058e74b')

def calculate_gradient(items):
    """Calculates the conic-gradient string for the donut chart."""
    gradient_parts = []
    current_percentage = 0
    for i, item in enumerate(items):
        # Use one of the 7 predefined chart colors, cycling through if necessary
        color_index = (i % 7) + 1
        color = f"var(--chart-color-{color_index})"
        
        start_percentage = current_percentage
        end_percentage = current_percentage + item.get('percentage_float', 0)
        
        # Clamp end_percentage to 100
        end_percentage = min(end_percentage, 100)

        gradient_parts.append(f"{color} {start_percentage:.2f}% {end_percentage:.2f}%")
        current_percentage = end_percentage
        
        # Stop if we've already filled the circle
        if current_percentage >= 100:
            break

    return ", ".join(gradient_parts)


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    API endpoint to generate a PDF report from JSON data using PDFShift.
    Expects a POST request with JSON body.
    """
    try:
        data = request.get_json()
        if not data:
            return "Error: No JSON data provided in the request.", 400

        # Read the HTML template from file
        with open('templates/pdf.html', 'r', encoding='utf-8') as f:
            template_string = f.read()

        # --- Data Preparation ---
        expense_items = data.get('expense_items', [])
        total_spent = sum(item.get('amount_float', 0) for item in expense_items)
        
        # Calculate percentages and add color variables for each expense item
        for i, item in enumerate(expense_items):
            percentage = (item.get('amount_float', 0) / total_spent) * 100 if total_spent > 0 else 0
            item['percentage_float'] = percentage
            item['percentage'] = f"{percentage:.0f}%"
            
            # Use one of the 7 predefined chart colors, cycling through if necessary
            color_index = (i % 7) + 1
            item['color'] = f"var(--chart-color-{color_index})"
            if color_index == 7:  # Add a border to the lightest color for visibility
                item['color'] += "; border: 1px solid #ddd;"

        # Generate the CSS conic-gradient string for the chart
        data['chart_gradient'] = calculate_gradient(expense_items)

        # --- HTML Rendering ---
        rendered_html = render_template_string(template_string, **data)

        # --- PDF Generation via PDFShift API ---
        api_url = 'https://api.pdfshift.io/v3/convert/pdf'
        
        headers = {
            'Content-Type': 'application/json'
        }
        # Use API Key if provided
        if PDFSHIFT_API_KEY:
            headers['X-API-Key'] = PDFSHIFT_API_KEY

        payload = {
            "source": rendered_html,
            "format": "A4",
            "sandbox": not bool(PDFSHIFT_API_KEY)  # Use sandbox if no API key
        }

        response = requests.post(api_url, headers=headers, json=payload)

        # Check if the API call was successful
        if response.status_code == 200:
            # Send the generated PDF back to the client
            return Response(response.content, mimetype='application/pdf')
        else:
            # Return the error from PDFShift
            error_message = f"Error from PDFShift API: {response.status_code} - {response.text}"
            print(error_message)
            return error_message, 500

    except Exception as e:
        # Log the error for debugging and return a generic server error
        print(f"An error occurred: {e}")
        return "An internal server error occurred.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))