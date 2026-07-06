# ZedConnect - A Zambia-focused Dating App

A simple, mobile-friendly dating web application built with FastAPI, SQLAlchemy, and SQLite.

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
ZedConnect/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration settings (JWT, app settings)
│   ├── database.py          # Database configuration (SQLAlchemy + SQLite)
│   ├── middleware.py        # CORS and other middlewares
│   ├── models.py            # Database models (User, Like, Message)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── users.py         # User profile routes
│   │   ├── matches.py       # Like and match routes
│   │   └── chat.py          # Chat routes
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic schemas for validation
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Main stylesheet
│   │   └── default_profile.png  # Default profile image
│   └── templates/
│       ├── base.html        # Base template
│       ├── home.html        # Home page
│       ├── register.html    # Registration page
│       ├── login.html         # Login page
│       ├── browse.html      # Browse users page
│       ├── profile.html     # User profile page
│       ├── view_profile.html # View other user's profile
│       ├── mutual.html      # Mutual matches page
│       ├── chat_list.html   # Chat list page
│       └── chat.html        # Chat conversation page
├── run.py                   # Run script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py
```

3. Open your browser and go to:
```
http://localhost:8000
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
- **SQLite** - Lightweight database
- **JWT** - Token-based authentication
- **Jinja2** - HTML templating
- **Passlib** - Password hashing

## License

MIT License - Feel free to use and modify!