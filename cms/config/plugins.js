module.exports = ({ env }) => {
  const plugins = {};

  // Email: only configure SendGrid when API key is present (not in local dev)
  if (env("SENDGRID_API_KEY")) {
    plugins.email = {
      config: {
        provider: "sendgrid",
        providerOptions: {
          apiKey: env("SENDGRID_API_KEY"),
        },
        settings: {
          defaultFrom: env("SENDGRID_FROM_EMAIL", "noreply@myvoya.ai"),
          defaultReplyTo: env("SENDGRID_FROM_EMAIL", "noreply@myvoya.ai"),
        },
      },
    };
  }

  // Upload: use S3 when bucket is configured, otherwise local filesystem
  if (env("AWS_S3_BUCKET")) {
    plugins.upload = {
      config: {
        provider: "aws-s3",
        providerOptions: {
          baseUrl: env("CDN_URL"),
          s3Options: {
            region: env("AWS_REGION", "us-east-1"),
            params: {
              Bucket: env("AWS_S3_BUCKET"),
            },
          },
        },
        actionOptions: {
          upload: { ACL: null },
          uploadStream: { ACL: null },
          delete: {},
        },
      },
    };
  }

  // MCP: enable in development only (exposes content types and services to AI tools)
  if (env("NODE_ENV", "production") === "development") {
    plugins.mcp = {
      enabled: true,
      config: {
        session: { type: "memory" },
      },
    };
  }

  return plugins;
};
