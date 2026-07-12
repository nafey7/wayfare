"""Email HTML template - pure template without logic.

This file contains ONLY the email template that can be edited by non-developers.
No Python logic, just template strings with placeholders.
"""

# ============================================================
# EMAIL HTML TEMPLATE
# ============================================================

EMAIL_TEMPLATE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }}
        .wrapper {{
            background-color: #f4f4f4;
            padding: 20px 0;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, {button_color} 0%, {button_color}dd 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .content p {{
            margin: 10px 0;
            line-height: 1.7;
        }}
        .button {{
            display: inline-block;
            padding: 14px 32px;
            background-color: {button_color};
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 25px 0;
            font-weight: 600;
            font-size: 16px;
            transition: opacity 0.3s;
        }}
        .button:hover {{
            opacity: 0.9;
        }}
        .button-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .link-box {{
            word-break: break-all;
            background: #f8f9fa;
            padding: 15px;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-family: monospace;
            font-size: 14px;
            color: #495057;
            margin: 20px 0;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            background-color: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }}
        .footer p {{
            margin: 5px 0;
        }}
        /* Responsive design */
        @media only screen and (max-width: 600px) {{
            .container {{
                width: 100% !important;
                border-radius: 0;
            }}
            .content {{
                padding: 20px 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>{title}</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                {body_content}
                {button_section}
            </div>
            <div class="footer">
                <p>{footer_text}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ============================================================
# EMAIL BUTTON SECTION (used when button_url is provided)
# ============================================================

EMAIL_BUTTON_SECTION = """
                <div class="button-container">
                    <a href="{button_url}" class="button">{button_text}</a>
                </div>
                <p style="color: #6c757d; font-size: 14px;">Or copy and paste this link into your browser:</p>
                <div class="link-box">{button_url}</div>"""

# ============================================================
# EMAIL TEXT TEMPLATE
# ============================================================

EMAIL_TEMPLATE_TEXT = """
{greeting}

{body_content}

{button_text}: {button_url}

{footer_text}
"""
