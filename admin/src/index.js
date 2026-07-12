import reportWebVitals from "./reportWebVitals";

import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "App";

// PMS Context Provider
import { MaterialUIControllerProvider } from "context";
import { Provider } from "react-redux";
import store from "store/store";
import { GoogleOAuthProvider } from "@react-oauth/google";

const container = document.getElementById("root");
const root = createRoot(container);

root.render(
  <Provider store={store}>
    <BrowserRouter>
      <MaterialUIControllerProvider>
        <GoogleOAuthProvider clientId="473136317892-641isf0e4i1521j6e37h3aiknukopfce.apps.googleusercontent.com">
          <App />
        </GoogleOAuthProvider>
      </MaterialUIControllerProvider>
    </BrowserRouter>
  </Provider>
);
// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();


// {
//   "credential": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImQ5NzQwYTcwYjA5NzJkY2NmNzVmYTg4YmM1MjliZDE2YTMwNTczYmQiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiI0NzMxMzYzMTc4OTItNjQxaXNmMGU0aTE1MjFqNmUzN2gzYWlrbnVrb3BmY2UuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJhdWQiOiI0NzMxMzYzMTc4OTItNjQxaXNmMGU0aTE1MjFqNmUzN2gzYWlrbnVrb3BmY2UuYXBwcy5nb29nbGV1c2VyY29udGVudC5jb20iLCJzdWIiOiIxMDQ4MjQ1NTkwMDYyNDI4Mzc3MDgiLCJlbWFpbCI6InNodWJoYW1raGVkZTk4QGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuYmYiOjE3MzI1MjgwNDMsIm5hbWUiOiJTaHViaGFtIEtoZWRlIiwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0lGS0ZyQXg3WXdwNkZsbGRWR1ZGR3QxOV9rVzFIQVhPRmZaLV9iOURwRGJ4VFRqd3JXPXM5Ni1jIiwiZ2l2ZW5fbmFtZSI6IlNodWJoYW0iLCJmYW1pbHlfbmFtZSI6IktoZWRlIiwiaWF0IjoxNzMyNTI4MzQzLCJleHAiOjE3MzI1MzE5NDMsImp0aSI6ImIwZjg5ZjRjNjI4MDY4ZjI1NGVmMDQ1Y2M0OGViYTc2NWQ2MjdlYTEifQ.D0gupNj9P2zAo1qtFpOLyQ_ZrD1QDYkR1xfnmxuWcW-6mR4QXFWinYGv7BnW-3fVhqcrhH2mOiNQ2sG-M9qnGAMN4DDOPfzuWHmHOCuJb4XfHck1ZJh8VgLMwV16rGYHYImmOIhCuX6L3YAF57o4Wb8qDXKtS7MUOMxo_dcMhykYEAifrURPh-68zYqOWAYJe6HPlkpxqNPompGPzQDVmE4dGlzrKe6KsM9ppOipP4bKNozAPEFDo0eK0nFn5Aqk_UzFv7Hc4vu4lSF3X7bSM71TJLCQSFTUAbvVz5yjFOeiWtVYV9xaVZE-35V9vKp958anFhgdGRhRGe-ariCnlg",
//   "clientId": "473136317892-641isf0e4i1521j6e37h3aiknukopfce.apps.googleusercontent.com",
//   "select_by": "btn"
// }
