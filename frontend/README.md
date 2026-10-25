# Nyaayukti Frontend

React + Vite frontend for Nyaayukti.

## Authentication flow

- Public Home and About pages remain accessible without an account.
- The navbar exposes a **Sign in** option.
- `/signin` supports both sign-in and account creation.
- Any chatbot CTA redirects an unauthenticated user to sign-in first.
- After a successful sign-in initiated from a chatbot CTA, the legal assistant opens automatically.
- The frontend sends the opaque auth session as `Authorization: Bearer <token>` to protected backend chat endpoints.
- An invalid or expired backend session automatically removes chatbot access.

## Local development

```bash
npm install
npm run dev
```

By default the frontend expects the Node API at `http://localhost:3000/api`. Override it with:

```env
VITE_API_BASE_URL=http://localhost:3000/api
```
