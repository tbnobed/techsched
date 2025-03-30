# Case-Insensitive Email Login Implementation

## Overview

This document explains how case-insensitive email login is implemented in the Plex Engineering Scheduler application.

## Implementation Details

### Login Authentication Method

The application implements case-insensitive email and username matching for login using SQLAlchemy's `func.lower()` function. This approach properly handles login attempts regardless of the capitalization used in the email address or username.

```python
# In auth.py login function
from sqlalchemy import func

# For email login
user = User.query.filter(func.lower(User.email) == func.lower(email_or_username)).first()

# For username login
user = User.query.filter(func.lower(User.username) == func.lower(email_or_username)).first()
```

### User Registration/Creation Method

Similarly, when checking if a user already exists during registration or user creation, we use the same case-insensitive approach:

```python
# In routes.py admin_create_user function
from sqlalchemy import func

# Check if email already exists (case-insensitive)
existing_email_user = User.query.filter(func.lower(User.email) == func.lower(email)).first()

# Check if username already exists (case-insensitive)
existing_user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
```

### Helper Method in User Model

The User model has a `check_email` helper method that can be used for case-insensitive email comparison in Python code:

```python
# In models.py User class
def check_email(self, email):
    """Case-insensitive email comparison - returns True if emails match ignoring case"""
    if not self.email or not email:
        return False
    return self.email.lower() == email.lower()
```

## Testing Case-Insensitive Login

A test script `direct_login.py` is available to verify that the case-insensitive login is working correctly. It tests various email formats and confirms that the login will succeed regardless of the case used in the email address.

## Important Notes

1. The application allows multiple accounts with the same email address in different capitalization formats to exist in the database (for backward compatibility).
2. When logging in, the system will find the first matching user account based on case-insensitive comparison.
3. Email normalization (converting to lowercase) happens at login time, not at storage time.
4. User registration functions check for case-insensitive duplicates to prevent new accounts with the same email in different capitalizations.