# Kavithedal Publications Backend

Django REST API Backend for Kavithedal Publications - A Publishing Company Website.

## Features

- **Admin Authentication**: JWT-based authentication with refresh tokens
- **Books Management**: Full CRUD operations with search, filter, and ordering
- **Authors Management**: Manage authors with their books
- **Testimonials**: Reader and author testimonials with approval workflow
- **Contests**: Writing contests management with deadline tracking
- **Public APIs**: View endpoints available for public users (books, authors, approved testimonials, active contests)

## Tech Stack

- **Backend**: Django 5.1 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (djangorestframework-simplejwt)
- **CORS**: django-cors-headers

## Project Structure

```
kavithedal_backend/
├── config/                 # Django project settings
│   ├── settings.py         # Main settings
│   ├── urls.py             # URL routing
│   └── wsgi.py             # WSGI config
├── apps/                   # Django applications
│   ├── accounts/           # Admin user management
│   ├── books/              # Books & categories
│   ├── authors/            # Authors management
│   ├── testimonials/       # Testimonials management
│   └── contests/           # Contests management
├── manage.py               # Django management script
└── requirements.txt        # Python dependencies
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Admin login
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/refresh/` - Refresh JWT token
- `GET /api/auth/users/me/` - Get current user
- `POST /api/auth/users/change_password/` - Change password

### Books
- `GET /api/books/` - List books (public)
- `POST /api/books/` - Create book (admin)
- `GET /api/books/{id}/` - Get book details
- `PUT /api/books/{id}/` - Update book (admin)
- `DELETE /api/books/{id}/` - Delete book (admin)
- `GET /api/books/featured/` - Get featured books
- `GET /api/books/recent/` - Get recent books

### Authors
- `GET /api/authors/` - List authors (public)
- `POST /api/authors/` - Create author (admin)
- `GET /api/authors/{id}/` - Get author details
- `PUT /api/authors/{id}/` - Update author (admin)
- `DELETE /api/authors/{id}/` - Delete author (admin)
- `GET /api/authors/{id}/books/` - Get author's books

### Testimonials
- `GET /api/testimonials/` - List approved testimonials (public)
- `POST /api/testimonials/` - Create testimonial (public)
- `GET /api/testimonials/{id}/` - Get testimonial
- `PUT /api/testimonials/{id}/` - Update testimonial (admin)
- `DELETE /api/testimonials/{id}/` - Delete testimonial (admin)
- `POST /api/testimonials/{id}/approve/` - Approve testimonial (admin)
- `POST /api/testimonials/{id}/reject/` - Reject testimonial (admin)
- `GET /api/testimonials/pending/` - Get pending testimonials (admin)

### Contests
- `GET /api/contests/` - List active contests (public)
- `POST /api/contests/` - Create contest (admin)
- `GET /api/contests/{id}/` - Get contest details
- `PUT /api/contests/{id}/` - Update contest (admin)
- `DELETE /api/contests/{id}/` - Delete contest (admin)
- `GET /api/contests/active/` - Get active contests
- `GET /api/contests/upcoming/` - Get upcoming contests

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL 14+

### 1. Clone and Setup Virtual Environment

```bash
cd kavithedal_backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `config/env.example` to `.env` and update values:

```bash
cp config/env.example .env
```

Edit `.env`:
```
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=kavithedal_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

### 4. Setup Database

```bash
# Create PostgreSQL database
createdb kavithedal_db

# Run migrations
python manage.py migrate
```

### 5. Create Admin User

```bash
# Interactive mode
python manage.py createadmin

# Or with arguments
python manage.py createadmin --email admin@kavithedal.com --username admin --password yourpassword
```

### 6. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## Frontend Setup

The frontend is already configured to connect to the backend. Make sure the backend is running before starting the frontend.

```bash
cd ..  # Go to frontend directory
npm install
npm run dev
```

## Permissions

- **Public**: Can view books, authors, approved testimonials, active contests
- **Admin**: Full CRUD access to all resources

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use environment variables for secrets
3. Configure a production database
4. Use a WSGI server like gunicorn:
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```
5. Configure static file serving (Whitenoise)
6. Use HTTPS in production
