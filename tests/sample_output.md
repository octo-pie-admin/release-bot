## Octo-Pie API v1.2.0 Released: Authentication & Comments

This release marks an exciting milestone for the Octo-Pie API, introducing essential features and improvements that enhance the developer experience. In this post, we'll dive into what's new and how it affects you.

### Highlights

* **Authentication Endpoints**: Secure your blog posts with user authentication.
* **Comment Support**: Engage with users through comment threads on your blog posts.
* Improved error handling and support for multiple HTTP methods.

## New Features

### Commenting on Blog Posts

We've added a new endpoint to allow users to add comments to your blog posts. With this feature, you can enable discussion on individual articles, fostering a community around your content.

**Sample Request and Response**

```json
// POST /comments
{
  "postId": "12345",
  "content": "This is an amazing post!"
}

// Response:
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id": "67890",
  "postId": "12345",
  "content": "This is an amazing post!",
  "author": "John Doe"
}
```

### Authentication Endpoints

We've introduced two new endpoints for user authentication:

*   **GET /auth/login**: Allows users to log in using their credentials.
*   **POST /auth/login**: For testing purposes or when you need more control over the login process.

**Sample Request and Response**

```http
// GET /auth/login
GET https://example.com/auth/login HTTP/1.1

// Response:
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token": "your-auth-token",
  "expiresIn": 3600 // token expires in 1 hour
}
```

```http
// POST /auth/login
POST https://example.com/auth/login HTTP/1.1

{
  "username": "johndoe@example.org",
  "password": "mysecretpassword"
}

// Response:
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token": "your-auth-token",
  "expiresIn": 3600 // token expires in 1 hour
}
```

## Improvements & Fixes

We've made several improvements to error handling, including:

*   **Error Code Changes**: We now return specific HTTP status codes for errors instead of a generic `500 Internal Server Error`. This helps with debugging and provides more informative error messages.

**Before vs. After Example**

**Old Behavior**
```http
GET /posts/12345 HTTP/1.1

// Response:
HTTP/1.1 500 Internal Server Error
```

**New Behavior**
```http
GET /posts/12345 HTTP/1.1

// Response:
HTTP/1.1 404 Not Found
```

We've also improved error handling for missing or invalid parameters in API requests.

```json
// Invalid Parameter Error
{
  "error": {
    "code": "invalidParameter",
    "message": "The parameter 'id' is required."
  }
}
```

**Example Request**

```http
GET /posts?title=Example HTTP/1.1

// Response:
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "invalidParameter",
    "message": "The parameter 'id' is required."
  }
}
```

## Closing

This release marks an exciting step forward for the Octo-Pie API, and we're thrilled to introduce these new features. We encourage you to explore our documentation at [docs](https://github.com/example-org/example-repo/releases/tag/v1.0.0) to learn more about the changes and how they can benefit your applications.