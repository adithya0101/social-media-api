#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Testing Social Media API ==="
echo

echo "1. Health Check"
curl -s $BASE_URL/health | jq
echo

echo "2. Register User"
REGISTER=$(curl -s -X POST $BASE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123"}')
echo $REGISTER | jq
echo

echo "3. Login"
LOGIN=$(curl -s -X POST $BASE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass123"}')
echo $LOGIN | jq

TOKEN=$(echo $LOGIN | jq -r '.access_token')
echo "Token: $TOKEN"
echo

echo "4. Get Current User"
curl -s $BASE_URL/users/me \
  -H "Authorization: Bearer $TOKEN" | jq
echo

echo "5. Create Post (no image)"
POST=$(curl -s -X POST $BASE_URL/posts \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Test Post" \
  -F "content=This is a test post")
echo $POST | jq

POST_ID=$(echo $POST | jq -r '.id')
echo

echo "6. Get All Posts"
curl -s "$BASE_URL/posts?skip=0&limit=10" | jq
echo

echo "7. Get Post by ID"
curl -s $BASE_URL/posts/$POST_ID | jq
echo

echo "8. Update Post"
curl -s -X PUT $BASE_URL/posts/$POST_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}' | jq
echo

echo "Done!"
