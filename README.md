# zedmatch - A Zambia-focused Dating App

A simple, mobile-friendly dating web application built with FastAPI, SQLAlchemy, and PostgreSQL (Neon).

## Features

- **User Registration & Login** - Secure authentication with JWT tokens
- **User Profiles** - Full name, age, gender, location (Zambia provinces), bio, and profile picture
- **Browse Users** - Discover other users in Zambia
- **Like System** - Swipe right to like users
- **Mutual Matches** - Get matched when both users like each other
- **Chat** - Basic messaging between matched users
- **Mobile-friendly Design** - Responsive CSS for all devices

## Project Structure

```
zedmatch/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration settings (JWT, app settings)
│   ├── database.py          # Database configuration (SQLAlchemy + PostgreSQL)
│   ├── middleware.py        # CORS and other middlewares
│   ├── models.py            # Database models (User, Like, Message, Notification)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── users.py         # User profile routes
│   │   ├── matches.py       # Like and match routes
│   │   ├── chat.py          # Chat routes
│   │   └── reports.py       # Report routes
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic schemas for validation
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Main stylesheet
│   │   ├── js/
│   │   │   └── webrtc.js    # WebRTC video calling
│   │   ├── default_profile.png  # Default profile image
│   │   └── chat_media/      # Uploaded chat media (gitignored)
│   └── templates/
│       ├── base.html        # Base template
│       ├── home.html        # Home page
│       ├── register.html    # Registration page
│       ├── login.html       # Login page
│       ├── browse.html      # Browse users page
│       ├── profile.html     # User profile page
│       ├── view_profile.html # View other user's profile
│       ├── mutual.html      # Mutual matches page
│       ├── chat_list.html   # Chat list page
│       └── chat.html        # Chat conversation page
├── run.py                   # Run script
├── requirements.txt         # Python dependencies
├── render.yaml              # Render deployment configuration
└── README.md               # This file
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/beenzuh20-rgb/zedmatch.git
cd zedmatch
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (copy `.env.example` to `.env` and fill in your values):
```bash
cp .env.example .env
```

4. Run the application:
```bash
python run.py
```

5. Open your browser and go to:
```
http://localhost:7777
```

## Zambia Provinces

The app is focused on Zambia and includes all provinces:
- Lusaka
- Copperbelt
- Central
- Eastern
- Luapula
- Northern
- North-Western
- Southern
- Western

## API Endpoints

### Authentication
- `GET /auth/register` - Registration page
- `POST /auth/register` - Register new user
- `GET /auth/login` - Login page
- `POST /auth/login` - Login user
- `GET /auth/logout` - Logout user

### Users
- `GET /users/profile` - View/edit own profile
- `GET /users/profile/{user_id}` - View another user's profile
- `POST /users/profile/edit` - Update profile

### Matches
- `GET /matches/browse` - Browse users to like
- `POST /matches/like/{user_id}` - Like a user
- `GET /matches/mutual` - View mutual matches

### Chat
- `GET /chat/` - List conversations
- `GET /chat/with/{user_id}` - Chat with a user
- `POST /chat/send/{user_id}` - Send a message

## Tech Stack

- **FastAPI** - Modern web framework
- **SQLAlchemy** - ORM for database
- **PostgreSQL (Neon)** - Cloud-hosted relational database
- **JWT** - Token-based authentication
- **Jinja2** - HTML templating
- **Passlib** - Password hashing
- **Cloudinary** - Image upload and CDN
- **WebRTC** - Video/audio calling

## Deployment on Render

This app is configured for deployment on [Render](https://render.com) with [Neon](https://neon.tech) PostgreSQL.

1. Push this repository to GitHub.
2. Create a new **Web Service** on Render and connect your GitHub repo.
3. Set the following environment variables in Render:
   - `SECRET_KEY` - Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `DATABASE_URL` - Your Neon PostgreSQL connection string (from Neon Console)
   - `CLOUDINARY_CLOUD_NAME` - Your Cloudinary cloud name
   - `CLOUDINARY_API_KEY` - Your Cloudinary API key
   - `CLOUDINARY_API_SECRET` - Your Cloudinary API secret
4. Deploy. Render will use `render.yaml` for build and start commands.

### Neon Console Setup

1. Create a project on [neon.tech](https://neon.tech).
2. Create a database and copy the **Connection string** (Prisma/PSQL format).
3. Paste it into Render's `DATABASE_URL` environment variable.
4. Ensure the connection string includes `?sslmode=require` (the app auto-appends it if missing).

## License

MIT License - Feel free to use and modify!

MIT License - Feel free to use and modify!