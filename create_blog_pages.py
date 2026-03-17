"""
Create initial pages for LovelyHomePicks Blogger blog.
Run: python create_blog_pages.py
Make sure token.json is authenticated with lovelyhomepicks@gmail.com
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from blogger_up import get_blogger_service
from config import BLOGGER_BLOG_ID, BLOG_URL as _BLOG_URL

BLOG_ID = BLOGGER_BLOG_ID
BLOG_URL = 'https://lovelyhomepicks.blogspot.com'
BLOG_NAME = 'LovelyHomePicks'
CONTACT_EMAIL = 'lovelyhomepicks@gmail.com'
YEAR = '2025'

PAGES = [
    {
        "title": "About Us",
        "content": f"""
<div style="max-width:800px;margin:0 auto;font-family:Georgia,serif;line-height:1.8;color:#333;padding:20px">

<h1 style="color:#c0392b;font-size:2em;border-bottom:2px solid #c0392b;padding-bottom:10px">About {BLOG_NAME}</h1>

<p>Welcome to <strong>{BLOG_NAME}</strong> — your go-to destination for beautiful, practical, and budget-friendly home decor inspiration.</p>

<p>We believe that a well-decorated home doesn't have to cost a fortune. Our team curates the best home decor finds, interior styling tips, and room transformation ideas to help you create the home of your dreams — regardless of your budget.</p>

<h2 style="color:#c0392b;margin-top:30px">What We Cover</h2>
<ul style="padding-left:20px">
  <li>Living room decor ideas &amp; inspiration</li>
  <li>Bedroom styling tips &amp; cozy aesthetics</li>
  <li>Kitchen &amp; dining room design</li>
  <li>Bathroom refresh ideas</li>
  <li>Home office setup &amp; decor</li>
  <li>Budget-friendly Amazon home finds</li>
  <li>Luxury looks for less</li>
</ul>

<h2 style="color:#c0392b;margin-top:30px">Our Promise</h2>
<p>Every product we recommend has been carefully researched and selected for its quality, style, and value. We only share items we genuinely believe will enhance your home.</p>

<h2 style="color:#c0392b;margin-top:30px">Get in Touch</h2>
<p>Have questions, suggestions, or collaboration inquiries? We'd love to hear from you!</p>
<p>📧 <a href="mailto:{CONTACT_EMAIL}" style="color:#c0392b">{CONTACT_EMAIL}</a></p>

<p style="margin-top:40px;font-style:italic;color:#777">Thank you for visiting {BLOG_NAME}. Happy decorating! 🏡</p>

</div>
"""
    },
    {
        "title": "Contact",
        "content": f"""
<div style="max-width:800px;margin:0 auto;font-family:Georgia,serif;line-height:1.8;color:#333;padding:20px">

<h1 style="color:#c0392b;font-size:2em;border-bottom:2px solid #c0392b;padding-bottom:10px">Contact Us</h1>

<p>We'd love to hear from you! Whether you have a question, feedback, or a collaboration inquiry, feel free to reach out.</p>

<h2 style="color:#c0392b;margin-top:30px">Get in Touch</h2>

<p>📧 <strong>Email:</strong> <a href="mailto:{CONTACT_EMAIL}" style="color:#c0392b">{CONTACT_EMAIL}</a></p>

<p>We typically respond within 1–2 business days.</p>

<h2 style="color:#c0392b;margin-top:30px">Business Inquiries</h2>
<p>For brand collaborations, sponsored content, or affiliate partnership inquiries, please include the following in your email:</p>
<ul style="padding-left:20px">
  <li>Your brand/company name</li>
  <li>Type of collaboration you're interested in</li>
  <li>Brief description of your product/service</li>
</ul>

<h2 style="color:#c0392b;margin-top:30px">Follow Us</h2>
<p>Stay up to date with our latest home decor finds and inspiration on Pinterest!</p>
<p>📌 <a href="https://www.pinterest.com/lovelyhomepicks" style="color:#c0392b" target="_blank">pinterest.com/lovelyhomepicks</a></p>

</div>
"""
    },
    {
        "title": "Privacy Policy",
        "content": f"""
<div style="max-width:800px;margin:0 auto;font-family:Georgia,serif;line-height:1.8;color:#333;padding:20px">

<h1 style="color:#c0392b;font-size:2em;border-bottom:2px solid #c0392b;padding-bottom:10px">Privacy Policy</h1>

<p><em>Last updated: January 1, {YEAR}</em></p>

<p>At <strong>{BLOG_NAME}</strong> ("{BLOG_URL}"), we are committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information.</p>

<h2 style="color:#c0392b;margin-top:30px">Information We Collect</h2>
<p>We may collect non-personally identifiable information such as browser type, pages visited, and time spent on the site through standard web analytics tools (Google Analytics).</p>

<h2 style="color:#c0392b;margin-top:30px">Cookies</h2>
<p>This site uses cookies to improve your browsing experience and to serve relevant advertisements. You can disable cookies in your browser settings, though this may affect site functionality.</p>
<p>Third-party vendors, including Google, use cookies to serve ads based on your prior visits. You can opt out of Google's use of cookies by visiting <a href="https://www.google.com/settings/ads" style="color:#c0392b" target="_blank">Google Ads Settings</a>.</p>

<h2 style="color:#c0392b;margin-top:30px">Third-Party Links</h2>
<p>Our blog contains links to third-party websites (such as Amazon). These sites have their own privacy policies, and we have no responsibility or liability for their content or activities.</p>

<h2 style="color:#c0392b;margin-top:30px">Google Analytics</h2>
<p>We use Google Analytics to understand how visitors interact with our site. Google Analytics collects data anonymously and reports website trends without identifying individual visitors.</p>

<h2 style="color:#c0392b;margin-top:30px">Children's Privacy</h2>
<p>This website is not directed at children under 13. We do not knowingly collect personal information from children.</p>

<h2 style="color:#c0392b;margin-top:30px">Changes to This Policy</h2>
<p>We may update this Privacy Policy from time to time. We encourage you to review this page periodically for any changes.</p>

<h2 style="color:#c0392b;margin-top:30px">Contact</h2>
<p>If you have questions about this Privacy Policy, please contact us at <a href="mailto:{CONTACT_EMAIL}" style="color:#c0392b">{CONTACT_EMAIL}</a>.</p>

</div>
"""
    },
    {
        "title": "Affiliate Disclaimer",
        "content": f"""
<div style="max-width:800px;margin:0 auto;font-family:Georgia,serif;line-height:1.8;color:#333;padding:20px">

<h1 style="color:#c0392b;font-size:2em;border-bottom:2px solid #c0392b;padding-bottom:10px">Affiliate Disclaimer</h1>

<p><em>Last updated: January 1, {YEAR}</em></p>

<div style="background:#fff8f8;border-left:4px solid #c0392b;padding:15px 20px;margin:20px 0;border-radius:4px">
<strong>Disclosure:</strong> {BLOG_NAME} is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon.com.
</div>

<h2 style="color:#c0392b;margin-top:30px">What This Means</h2>
<p>Some of the links on this blog are affiliate links. This means that if you click on a link and make a purchase, we may receive a small commission — <strong>at no extra cost to you</strong>. This helps us keep the blog running and continue providing free content.</p>

<h2 style="color:#c0392b;margin-top:30px">Our Commitment to You</h2>
<p>We only recommend products that we genuinely believe will add value to your home and life. Affiliate commissions do <strong>not</strong> influence our editorial content or product recommendations. Our goal is always to provide honest, helpful information.</p>

<h2 style="color:#c0392b;margin-top:30px">Other Affiliate Programs</h2>
<p>In addition to Amazon, we may also participate in other affiliate programs including but not limited to:</p>
<ul style="padding-left:20px">
  <li>ShareASale network merchants</li>
  <li>Impact network merchants</li>
  <li>Wayfair Affiliate Program</li>
  <li>Other home decor brand affiliate programs</li>
</ul>
<p>All affiliate relationships are disclosed in compliance with the FTC's guidelines.</p>

<h2 style="color:#c0392b;margin-top:30px">Questions?</h2>
<p>If you have any questions about our affiliate relationships, please contact us at <a href="mailto:{CONTACT_EMAIL}" style="color:#c0392b">{CONTACT_EMAIL}</a>.</p>

</div>
"""
    }
]


def create_pages():
    print("Connecting to Blogger API...")
    service = get_blogger_service()

    print(f"Creating pages for Blog ID: {BLOG_ID}\n")

    for page in PAGES:
        print(f"  Creating page: {page['title']}...")
        try:
            result = service.pages().insert(
                blogId=BLOG_ID,
                body={
                    "title": page["title"],
                    "content": page["content"]
                }
            ).execute()
            print(f"  ✅ Created: {result.get('url', 'no url')}")
        except Exception as e:
            print(f"  ❌ Failed: {e}")

    print("\nDone! All pages created.")
    print(f"View at: {BLOG_URL}/p/about-us.html")


if __name__ == "__main__":
    create_pages()
