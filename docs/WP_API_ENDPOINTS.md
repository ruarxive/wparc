# WordPress REST API Endpoints Documentation

This document provides comprehensive documentation for WordPress REST API endpoints accessible via `/wp-json/`.

## Table of Contents

- [Overview](#overview)
- [Core WordPress Endpoints (wp/v2)](#core-wordpress-endpoints-wpv2)
- [Plugin Endpoints](#plugin-endpoints)
- [Endpoint Categories](#endpoint-categories)
- [Usage Examples](#usage-examples)
- [Authentication](#authentication)

## Overview

The WordPress REST API provides a standardized way to interact with WordPress sites. All endpoints are accessible under the `/wp-json/` path. The API follows RESTful principles and returns JSON data.

### Base URL Format

```
http://example.com/wp-json/
https://example.com/wp-json/
```

### API Discovery

To discover all available endpoints, access the root endpoint:

```
GET /wp-json/
```

This returns a JSON object containing:
- `name`: Site name
- `description`: Site description
- `url`: Site URL
- `home`: Home URL
- `namespaces`: Available API namespaces
- `routes`: All available routes with their endpoints and methods

## Core WordPress Endpoints (wp/v2)

The `wp/v2` namespace contains the core WordPress REST API endpoints. These are available in WordPress 4.7+.

### Content Endpoints

#### Posts
- **Endpoint**: `/wp/v2/posts`
- **Method**: GET
- **Description**: Retrieve a collection of posts
- **Pagination**: Yes (supports `page`, `per_page`, `offset`)
- **Query Parameters**:
  - `page`: Page number (default: 1)
  - `per_page`: Items per page (default: 10, max: 100)
  - `search`: Search query
  - `after`: Date after (ISO 8601)
  - `before`: Date before (ISO 8601)
  - `author`: Author ID
  - `categories`: Category IDs (comma-separated)
  - `tags`: Tag IDs (comma-separated)
  - `status`: Post status (default: publish)
  - `orderby`: Sort field (date, title, etc.)
  - `order`: Sort direction (asc, desc)

**Example**:
```bash
GET /wp-json/wp/v2/posts?per_page=100&page=1
```

#### Pages
- **Endpoint**: `/wp/v2/pages`
- **Method**: GET
- **Description**: Retrieve a collection of pages
- **Pagination**: Yes
- **Query Parameters**: Similar to posts endpoint

#### Media
- **Endpoint**: `/wp/v2/media`
- **Method**: GET
- **Description**: Retrieve a collection of media items
- **Pagination**: Yes
- **Query Parameters**:
  - `media_type`: Filter by media type (image, video, audio, application)
  - `mime_type`: Filter by MIME type
  - `parent`: Parent post ID

**Example**:
```bash
GET /wp-json/wp/v2/media?per_page=100&media_type=image
```

#### Comments
- **Endpoint**: `/wp/v2/comments`
- **Method**: GET
- **Description**: Retrieve a collection of comments
- **Pagination**: Yes
- **Query Parameters**:
  - `post`: Filter by post ID
  - `parent`: Filter by parent comment ID
  - `author`: Filter by author ID
  - `status`: Comment status

### Taxonomy Endpoints

#### Categories
- **Endpoint**: `/wp/v2/categories`
- **Method**: GET
- **Description**: Retrieve a collection of categories
- **Pagination**: Yes
- **Query Parameters**:
  - `search`: Search query
  - `parent`: Filter by parent category ID
  - `post`: Filter by post ID
  - `orderby`: Sort field (id, count, name, slug)
  - `order`: Sort direction (asc, desc)

#### Tags
- **Endpoint**: `/wp/v2/tags`
- **Method**: GET
- **Description**: Retrieve a collection of tags
- **Pagination**: Yes
- **Query Parameters**: Similar to categories

### User Endpoints

#### Users
- **Endpoint**: `/wp/v2/users`
- **Method**: GET
- **Description**: Retrieve a collection of users
- **Pagination**: Yes
- **Query Parameters**:
  - `search`: Search query
  - `roles`: Filter by role (comma-separated)
  - `who`: Filter by who (authors)
  - `orderby`: Sort field (id, name, registered_date, slug)
  - `order`: Sort direction (asc, desc)

**Note**: User data may be limited based on permissions. The `/wp/v2/users/me` endpoint requires authentication.

### Search Endpoint

#### Search
- **Endpoint**: `/wp/v2/search`
- **Method**: GET
- **Description**: Search across post types
- **Pagination**: Yes
- **Query Parameters**:
  - `search`: Search query (required)
  - `type`: Post types to search (comma-separated)
  - `subtype`: Post subtypes to search

### Metadata Endpoints

#### Types
- **Endpoint**: `/wp/v2/types`
- **Method**: GET
- **Description**: Retrieve registered post types
- **Pagination**: No
- **Returns**: Dictionary of post type objects

#### Taxonomies
- **Endpoint**: `/wp/v2/taxonomies`
- **Method**: GET
- **Description**: Retrieve registered taxonomies
- **Pagination**: No
- **Returns**: Dictionary of taxonomy objects

#### Statuses
- **Endpoint**: `/wp/v2/statuses`
- **Method**: GET
- **Description**: Retrieve available post statuses
- **Pagination**: No
- **Returns**: Dictionary of status objects

### Blocks Endpoint

#### Blocks
- **Endpoint**: `/wp/v2/blocks`
- **Method**: GET
- **Description**: Retrieve reusable blocks (Gutenberg)
- **Pagination**: Yes
- **Query Parameters**: Similar to posts endpoint

## Plugin Endpoints

Many WordPress plugins add their own REST API endpoints. Common plugin namespaces include:

### Yoast SEO (`/yoast/v1`)
- `/yoast/v1`: Plugin information
- `/yoast/v1/myyoast`: MyYoast integration
- `/yoast/v1/indexing/*`: Indexing endpoints (protected)

### Jetpack (`/jetpack/v4`)
- `/jetpack/v4`: Plugin information
- `/jetpack/v4/connection`: Connection status
- `/jetpack/v4/site`: Site information
- `/jetpack/v4/module/*`: Module management (protected)
- `/jetpack/v4/settings`: Settings (protected)

### Contact Form 7 (`/contact-form-7/v1`)
- `/contact-form-7/v1`: Plugin information
- `/contact-form-7/v1/contact-forms`: List of contact forms

### WooCommerce (`/wc/v3`)
- `/wc/v3`: API information
- `/wc/v3/products`: Products
- `/wc/v3/orders`: Orders (protected)
- `/wc/v3/customers`: Customers (protected)

### The Events Calendar (`/tribe/events/v1`)
- `/tribe/events/v1`: API information
- `/tribe/events/v1/events`: Events
- `/tribe/events/v1/venues`: Venues
- `/tribe/events/v1/organizers`: Organizers
- `/tribe/events/v1/categories`: Event categories
- `/tribe/events/v1/tags`: Event tags

### Other Common Plugins

- **Akismet** (`/akismet/v1`): Spam protection
- **Wordfence** (`/wordfence/v1`): Security plugin
- **Redirection** (`/redirection/v1`): URL redirection management
- **WP Super Cache** (`/wp-super-cache/v1`): Caching plugin
- **All in One SEO** (`/aioseo/v1`): SEO plugin
- **Meta Slider** (`/metaslider/v1`): Slider plugin
- **Real Media Library** (`/realmedialibrary/v1`): Media organization

## Endpoint Categories

In the `wparc` project, endpoints are categorized based on their behavior and accessibility:

### Public List Endpoints (`public-list`)

These endpoints return paginated lists of items. They support:
- Pagination (`page`, `per_page`)
- Filtering and sorting
- Return arrays of objects

**Examples**:
- `/wp/v2/posts`
- `/wp/v2/pages`
- `/wp/v2/media`
- `/wp/v2/categories`
- `/wp/v2/tags`
- `/wp/v2/users`
- `/wp/v2/comments`

### Public Dictionary Endpoints (`public-dict`)

These endpoints return single objects or dictionaries. They:
- Do not support pagination
- Return a single JSON object
- Often provide metadata or configuration

**Examples**:
- `/wp/v2` - API information
- `/wp/v2/types` - Post types
- `/wp/v2/taxonomies` - Taxonomies
- `/wp/v2/statuses` - Post statuses
- `/oembed/1.0` - oEmbed information

### Protected Endpoints (`protected`)

These endpoints require authentication. They typically:
- Require user authentication (OAuth, Application Passwords, etc.)
- Provide administrative or user-specific data
- May modify site data

**Examples**:
- `/wp/v2/users/me` - Current user information
- `/wp/v2/settings` - Site settings
- `/wp/v2/themes` - Installed themes
- `/wp/v2/plugins` - Installed plugins
- `/jetpack/v4/module/*` - Jetpack module management

### Useless Endpoints (`useless`)

These endpoints are not useful for data extraction because they:
- Are individual item endpoints (already covered by list endpoints)
- Handle revisions or autosaves
- Are write-only endpoints
- Are batch operations

**Examples**:
- `/wp/v2/posts/(?P<id>[\d]+)` - Single post (use list endpoint instead)
- `/wp/v2/posts/(?P<parent>[\d]+)/revisions` - Post revisions
- `/batch/v1` - Batch operations
- `/oembed/1.0/embed` - oEmbed proxy

## Usage Examples

### Discovering Available Endpoints

```bash
# Get all available routes
curl https://example.com/wp-json/ | jq '.routes | keys'
```

### Retrieving Posts

```bash
# Get first 100 posts
curl "https://example.com/wp-json/wp/v2/posts?per_page=100&page=1"

# Search posts
curl "https://example.com/wp-json/wp/v2/posts?search=wordpress"

# Get posts by category
curl "https://example.com/wp-json/wp/v2/posts?categories=5"
```

### Retrieving Media

```bash
# Get all images
curl "https://example.com/wp-json/wp/v2/media?per_page=100&media_type=image"

# Get media for a specific post
curl "https://example.com/wp-json/wp/v2/media?parent=123"
```

### Retrieving Taxonomies

```bash
# Get all categories
curl "https://example.com/wp-json/wp/v2/categories?per_page=100"

# Get all tags
curl "https://example.com/wp-json/wp/v2/tags?per_page=100"
```

### Using wparc

The `wparc` tool automatically handles endpoint discovery and data extraction:

```bash
# Discover and dump all public endpoints
wparc dump example.com

# This will:
# 1. Discover all available routes from /wp-json/
# 2. Categorize them based on known_routes.yml
# 3. Extract data from public-list and public-dict endpoints
# 4. Save data to <domain>/data/ directory
```

## Authentication

Most WordPress REST API endpoints are publicly accessible for reading. However, some endpoints require authentication:

### Authentication Methods

1. **Application Passwords** (WordPress 5.6+)
   - Generate in User Profile → Application Passwords
   - Use Basic Authentication: `Authorization: Basic base64(username:password)`

2. **OAuth 1.0a**
   - Requires OAuth plugin
   - More complex setup

3. **Cookie Authentication**
   - For logged-in users
   - Requires nonce verification

### Protected Endpoints

Endpoints that typically require authentication:
- User-specific data (`/wp/v2/users/me`)
- Site settings (`/wp/v2/settings`)
- Plugin/theme management
- Content creation/modification
- Administrative functions

### Public Endpoints

These endpoints are publicly accessible:
- Posts, pages, media (published content)
- Categories, tags, taxonomies
- Public user information
- Search functionality
- Most plugin data endpoints

## Response Format

All endpoints return JSON. List endpoints return arrays:

```json
[
  {
    "id": 1,
    "date": "2023-01-01T00:00:00",
    "title": {
      "rendered": "Post Title"
    },
    "content": {
      "rendered": "Post content..."
    },
    "_links": {
      "self": [{"href": "https://example.com/wp-json/wp/v2/posts/1"}]
    }
  }
]
```

Dictionary endpoints return objects:

```json
{
  "name": "post",
  "slug": "post",
  "description": "",
  "hierarchical": false,
  "rest_base": "posts",
  "supports": {
    "title": true,
    "editor": true
  }
}
```

## Pagination

List endpoints support pagination using query parameters:

- `page`: Page number (1-indexed)
- `per_page`: Items per page (default: 10, max: 100)
- `offset`: Skip N items (alternative to page)

Response headers include pagination information:
- `X-WP-Total`: Total number of items
- `X-WP-TotalPages`: Total number of pages

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Endpoint or resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object:

```json
{
  "code": "rest_invalid_param",
  "message": "Invalid parameter(s): per_page",
  "data": {
    "status": 400,
    "params": {
      "per_page": "per_page must be between 1 and 100"
    }
  }
}
```

## Best Practices

1. **Use pagination**: Always paginate large collections
2. **Respect rate limits**: Don't overwhelm the server
3. **Cache responses**: Cache static data when possible
4. **Handle errors**: Implement proper error handling
5. **Use HTTPS**: Always use HTTPS in production
6. **Filter data**: Request only needed fields when possible

## References

- [WordPress REST API Handbook](https://developer.wordpress.org/rest-api/)
- [WordPress REST API Reference](https://developer.wordpress.org/rest-api/reference/)
- [wparc Project](https://github.com/ruarxive/wparc)

