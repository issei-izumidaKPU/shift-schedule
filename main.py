from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd
import aiofiles
import os
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# This allows HTTP requests for OAuth (not recommended for production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Herokuのドメイン名を使う
HEROKU_DOMAIN = "https://shiftupload.herokuapp.com"

@app.get("/", response_class=HTMLResponse)
async def google_auth(request: Request):
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        SCOPES,
        redirect_uri=f'{HEROKU_DOMAIN}/oauth2callback'
    )
    auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent', include_granted_scopes='true')
    return RedirectResponse(url=auth_url)

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        SCOPES,
        redirect_uri=f'{HEROKU_DOMAIN}/oauth2callback'
    )
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials
    async with aiofiles.open('.token.json', 'w') as token_file:
        await token_file.write(credentials.to_json())
    return RedirectResponse(url="/upload")

@app.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_shift(file: UploadFile = File(...)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file format")
    
    async with aiofiles.open(f"/tmp/{file.filename}", 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # Load the Excel file
    df = pd.read_excel(f"/tmp/{file.filename}", header=0)
    print("DataFrame columns:", df.columns.tolist())  # Debugging: Print column names

    if '月日' not in df.columns:
        raise HTTPException(status_code=400, detail=f"'月日' column not found in the file. Columns found: {df.columns.tolist()}")

    async with aiofiles.open('.token.json', 'r') as token_file:
        token_info = await token_file.read()
    creds = Credentials.from_authorized_user_info(eval(token_info), SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    for col in df.columns[2:]:  # Assuming first two columns are date and day
        for index, row in df.iterrows():
            if pd.notna(row[col]):
                time_parts = row[col].split('-')
                if len(time_parts) != 2:
                    print(f"Skipping invalid time format in row {index + 1} for {col}")
                    continue
                start_time, end_time = time_parts
                date = row['月日'].strftime('%Y-%m-%d')  # Format date as 'YYYY-MM-DD'
                start_date_time = f"{date}T{start_time}:00+09:00"
                end_date_time = f"{date}T{end_time}:00+09:00"
                event = {
                    'summary': f'Work Shift - {col}',
                    'start': {'dateTime': start_date_time, 'timeZone': 'Asia/Tokyo'},
                    'end': {'dateTime': end_date_time, 'timeZone': 'Asia/Tokyo'},
                }
                print("Event to be inserted:", event)  # Debugging: Print the event data
                service.events().insert(calendarId='primary', body=event).execute()

    return {"message": "Shifts successfully uploaded to Google Calendar"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
