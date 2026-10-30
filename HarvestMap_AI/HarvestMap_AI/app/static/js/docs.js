"use strict";
window.addEventListener("DOMContentLoaded", () => {
  window.ui = SwaggerUIBundle({
    url: "/openapi.json",
    dom_id: "#swagger-ui",
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis],
    layout: "BaseLayout",
    persistAuthorization: false,
    requestInterceptor: (request) => {
      const csrf = document.cookie
        .split("; ")
        .find((c) => c.startsWith("harvest_csrf="))
        ?.split("=")[1];
      if (csrf) request.headers["X-CSRF-Token"] = decodeURIComponent(csrf);
      return request;
    },
  });
});
