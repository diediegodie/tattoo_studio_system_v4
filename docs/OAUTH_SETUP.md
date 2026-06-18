# Google OAuth and Calendar Setup

## Google Cloud Console
1. Go to the [Google Cloud Console](https://console.cloud.google.com).
2. Create a new project or select an existing one.
3. Enable the following APIs:
   - Google OAuth
   - Google Calendar

## Create OAuth Client
1. Navigate to "APIs & Services" > "Credentials".
2. Click "Create Credentials" > "OAuth client ID".
3. Select "Web Application" as the application type.
4. Add the following redirect URIs:
   - Local: `http://localhost:5000/auth/google_login/authorized`
   - Production: `https://your-app.onrender.com/auth/google_login/authorized`
5. Set the required scopes:
   - For authentication: `openid`, `email`, `profile`
   - For calendar access: `calendar.readonly`, `calendar.events`
6. Save the client ID and client secret for use in your application configuration.