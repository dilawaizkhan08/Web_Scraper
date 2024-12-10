from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from playwright.sync_api import sync_playwright
import pandas as pd
import os
from flask_cors import CORS
import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
CORS(app)

users = {
    "testuser": "password123"  # username: password
}

def extract_data(xpath, data_list, page, timeout=5000):
    try:
        if page.locator(xpath).count() > 0:
            data = page.locator(xpath).inner_text(timeout=timeout)
            data_list.append(data)
        else:
            data_list.append("N/A")  # Default value if element is missing
    except Exception as e:
        print(f"Skipping element at {xpath} due to timeout/error: {e}")
        data_list.append("N/A")  # Default value if data can't be fetched

def scrape_data(search_for, total=10):
    names_list, address_list, website_list, phones_list = [], [], [], []
    reviews_c_list, reviews_a_list = [], []
    store_s_list, in_store_list, store_del_list = [], [], []
    place_t_list, open_list, intro_list = [], [], []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.google.com/maps")
        page.wait_for_selector('//input[@id="searchboxinput"]')

        page.locator('//input[@id="searchboxinput"]').fill(search_for)
        page.keyboard.press("Enter")
        page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]')

        previously_counted = 0
        while True:
            page.mouse.wheel(0, 1000000)
            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]')
            if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() >= total:
                listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
                listings = [listing.locator("xpath=..") for listing in listings]
                break
            else:
                current_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                if current_count == previously_counted:
                    listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                    break
                previously_counted = current_count

        for listing in listings:
            listing.click()
            page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]')

            name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
            address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
            website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
            phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
            reviews_count_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]'
            reviews_average_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]'
            info1 = '//div[@class="LTs0Rc"][1]'
            opens_at_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
            place_type_xpath = '//div[@class="LBgpqf"]//button[@class="DkEaL "]'
            intro_xpath = '//div[@class="WeS02d fontBodyMedium"]//div[@class="PYvSYb "]'

            extract_data(name_xpath, names_list, page)
            extract_data(address_xpath, address_list, page)
            extract_data(website_xpath, website_list, page)
            extract_data(phone_number_xpath, phones_list, page)
            extract_data(place_type_xpath, place_t_list, page)
            extract_data(intro_xpath, intro_list, page)

            # Safe extraction for specific elements
            try:
                reviews_count = page.locator(reviews_count_xpath).inner_text(timeout=5000) if page.locator(reviews_count_xpath).count() > 0 else ""
                reviews_c_list.append(reviews_count.replace('(', '').replace(')', '').replace(',', ''))

                reviews_average = page.locator(reviews_average_xpath).inner_text(timeout=5000) if page.locator(reviews_average_xpath).count() > 0 else ""
                reviews_a_list.append(reviews_average.replace(' ', '').replace(',', '.'))

                store_s_list.append("Yes" if 'shop' in page.locator(info1).inner_text(timeout=5000) else "No")
                in_store_list.append("Yes" if 'pickup' in page.locator(info1).inner_text(timeout=5000) else "No")
                store_del_list.append("Yes" if 'delivery' in page.locator(info1).inner_text(timeout=5000) else "No")
            except Exception as e:
                print(f"Skipping store info due to timeout error: {e}")
                store_s_list.append("No")
                in_store_list.append("No")
                store_del_list.append("No")

            opening_time = page.locator(opens_at_xpath).inner_text(timeout=5000) if page.locator(opens_at_xpath).count() > 0 else ""
            open_list.append(opening_time)

        # DataFrame construction and CSV output
        df = pd.DataFrame({
            'Names': names_list, 'Website': website_list, 'Introduction': intro_list,
            'Phone Number': phones_list, 'Address': address_list, 'Review Count': reviews_c_list,
            'Average Review Count': reviews_a_list, 'Store Shopping': store_s_list,
            'In Store Pickup': in_store_list, 'Delivery': store_del_list,
            'Type': place_t_list, 'Opens At': open_list
        })

        df.drop_duplicates(subset=['Names', 'Phone Number', 'Address'], inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        df.to_csv('result.csv', index=False)

        csv_file_path = 'result.csv'

        print(f"CSV file generated at: {csv_file_path}")
        print("CSV file contents:")
        print(df.to_string(index=False))
        browser.close()
        return df
    

# def make_call(phone_number, customer_number, message=None):
#     try:
#         # Use the provided message or default to a generic one
#         if message is None:
#             message = "Hello, this is a test call."

#         # Prepare the payload for the VAPI API
#         payload = {
#             "assistantId": "e32e3b55-c9ca-471f-988a-274fc54d7f00",  # Your Assistant ID
#             "name": "Sarah",  # Assistant name
#             "assistant": {
#                 "transcriber": {
#                     "provider": "assembly-ai"  # Transcriber provider
#                 },
#                 "model": {
#                     "provider": "groq",  # Model provider
#                     "model": "llama-3.1-70b-versatile"  # Your model name
#                 },
#                 "firstMessage": message,  # Dynamic message
#             },
#             "phoneNumber": {
#                 "twilioAccountSid": os.getenv("TWILIO_SID"),  # Twilio Account SID
#                 "twilioAuthToken": os.getenv("TWILIO_TOKEN"),  # Twilio Auth Token
#                 "twilioPhoneNumber": os.getenv("TWILIO_NUMBER"),  # Twilio Phone Number
#                 "recipientPhoneNumber": phone_number  # Destination phone number
#             }
#         }

#         # Make the API call
#         api_url = "https://api.vapi.ai/call"
#         response = requests.post(api_url, json=payload)
#         response_data = response.json()

#         if response.status_code == 200:
#             print(f"Call successfully initiated to {phone_number} with message: {message}")
#         else:
#             error_message = response_data.get('error', 'Unknown error')
#             print(f"Failed to initiate call. Error: {error_message}")

#         return response_data
#     except Exception as e:
#         print(f"An error occurred while making the call: {e}")
#         return {"error": str(e)}



def make_call(phone_number, customer_number, message):
    try:
        # VAPI API endpoint and request payload
        payload = {
            "assistantId": "e32e3b55-c9ca-471f-988a-274fc54d7f00",  # Your Assistant ID
            "name": "Sarah",  # Your Assistant name
            "assistant": {
                "transcriber": {
                    "provider": "assembly-ai"  # Transcriber provider
                },
                "model": {
                    "provider": "groq",  # Model provider
                    "model": "llama-3.1-70b-versatile",  # Your model name
                    "systemPrompt": "You are an assistant calling businesses. Your task is to ask them about their business"
                },
                "firstMessage": message,
            },
            "phoneNumber": {
                "twilioAccountSid": os.getenv("TWILIO_SID"),  # Twilio Account SID
                "twilioAuthToken": os.getenv("TWILIO_TOKEN"),  # Twilio Auth Token
                "twilioPhoneNumber": os.getenv("TWILIO_NUMBER"),  # Twilio phone number
            },
            "customer": {
                "number": customer_number  # Customer phone number
            }
        }

        headers = {
            "Authorization": "Bearer dba9cfc4-e4b6-49a8-a341-2898a7c827bb",  # VAPI Bearer token
            "Content-Type": "application/json"
        }

        # Make the API call to VAPI
        response = requests.post("https://api.vapi.ai/call", json=payload, headers=headers)
        
        # Check for errors in the response
        response.raise_for_status()

        # Return response JSON
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Error making call to {phone_number}: {e}")
        return {"error": str(e)}
    

# # Example usage:
customer_number = "+923116805861"  # Customer's phone number
# result = make_call("+19083864875", customer_number)
# print(result)

# def call_all_numbers_from_csv(csv_path):
#     try:
#         df = pd.read_csv(csv_path)
#         if 'Phone Number' not in df.columns:
#             print("No phone numbers found in the CSV.")
#             return {"message": "No phone numbers found."}

#         # Loop through unique phone numbers and make calls
#         for number in df['Phone Number'].dropna().unique():
#             result = make_call("+19083864875", number)  # Adjust parameters as needed
#             print(f"Call result for {number}: {result}")
#             time.sleep(2)  # Add a delay between calls to avoid API rate limits
#     except Exception as e:
#         print(f"Error reading CSV or making calls: {e}")

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Simple authentication (replace with your DB logic)
    if users.get(username) == password:
        session['username'] = username  # Set session data
        return redirect(url_for('query'))
    else:
        return render_template('login.html', error="Invalid credentials")

@app.route('/query', methods=['GET', 'POST'])
def query():
    if 'username' not in session:
        return redirect(url_for('index'))  # Redirect to login if not logged in

    if request.method == 'POST':
        search_term = request.json.get('search_term')
        message = request.json.get('message')
        # prompt = request.json.get('prompt')
        if not search_term:
            return jsonify({"error": "Search term is required"}), 400
        data = scrape_data(search_term, total=10)
        # csv_file_path = 'result.csv'
        # call_all_numbers_from_csv(csv_file_path)  # Call VAPI numbers from the CSV

        make_call("+19083864875", customer_number, message)
        return data.to_dict(orient='records')
        
    return render_template('query.html')


# @app.route('/query', methods=['GET', 'POST'])
# def query():
#     if 'username' not in session:
#         return redirect(url_for('index'))  # Redirect to login if not logged in

#     if request.method == 'POST':
#         # Get the search term and optional message from the request
#         search_term = request.json.get('search_term')
#         message = request.json.get('message', "Hello, this is a default query call.")  # Default message

#         if not search_term:
#             return jsonify({"error": "Search term is required"}), 400

#         # Process the query and initiate the call
#         data = scrape_data(search_term, total=10)
#         customer_number = "+19083864875"  # Example dynamic number
#         make_call("+19083864875", customer_number, message=message)

#         return jsonify({"data": data.to_dict(orient='records'), "message": message})

#     return render_template('query.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove user from session
    return redirect(url_for('index'))  # Redirect to login page

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

    
