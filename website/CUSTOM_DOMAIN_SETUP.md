# QAMill Website - achieverthoughts.com Integration

## 🎯 Integration Options

Choose how you want to integrate QAMill into your existing domain:

### Option 1: Subdomain (Recommended)
```
https://qamill.achieverthoughts.com
```
✅ Clean, professional  
✅ Easy to manage  
✅ Separate from main site  
✅ Better for SEO  

### Option 2: Subfolder
```
https://achieverthoughts.com/qamill
```
✅ Simple setup  
✅ Shares main domain authority  
✅ No DNS changes needed  
✅ Integrated feel  

### Option 3: Path on Root
```
https://achieverthoughts.com
```
✅ Replace main site  
✅ Central hub for all services  
❌ Requires rebuilding other content  

---

## 📋 Setup Guide - Choose Your Hosting

### **If You Use: Shared Hosting (cPanel, Plesk, etc.)**

#### **Step 1: Create Subdomain (qamill.achieverthoughts.com)**
```
1. Login to cPanel/Plesk control panel
2. Go to: Addon Domains OR Subdomains
3. Create subdomain: qamill
4. Document Root: /public_html/qamill
5. Click Create
```

#### **Step 2: Upload Website Files**
```
1. Open FTP client (FileZilla, WinSCP)
2. Connect to: achieverthoughts.com
   - Host: ftp.achieverthoughts.com
   - Username: your_cpanel_username
   - Password: your_cpanel_password
   - Port: 21

3. Navigate to: /public_html/qamill/
4. Upload all website files:
   - index.html
   - styles.css
   - script.js
   - logo.svg (add yours)
   - hero-banner.png (add yours)

5. Verify files uploaded
```

#### **Step 3: Enable HTTPS**
```
1. In cPanel: SSL/TLS
2. Select domain: qamill.achieverthoughts.com
3. If AutoSSL available: Install
   - Otherwise: Purchase or use Let's Encrypt
4. Force HTTPS:
   - Add to .htaccess:
```

```apache
# Force HTTPS in .htaccess
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>
```

#### **Step 4: Test**
```
1. Visit: https://qamill.achieverthoughts.com
2. Check: Homepage loads
3. Test: All navigation links work
4. Verify: Slideshow functions (arrow keys, zoom, dots)
5. Mobile: Test on phone/tablet
```

---

### **If You Use: Netlify**

#### **Step 1: Deploy Website**
```
1. Login to Netlify
2. Create New Site
3. Choose: Deploy manually
4. Drag & drop website/ folder
5. Netlify creates temporary domain
```

#### **Step 2: Connect Custom Domain**
```
1. In Netlify: Site Settings
2. Domain Management → Add custom domain
3. Enter: qamill.achieverthoughts.com
4. Follow: Netlify's DNS setup instructions
```

#### **Step 3: Update DNS Records**
```
In your achieverthoughts.com DNS provider (GoDaddy, Cloudflare, etc.):

Add CNAME record:
Name: qamill
Type: CNAME
Value: [your-netlify-domain].netlify.app

TTL: 3600 (default)
```

#### **Step 4: Verify & Done**
```
1. Wait 5-15 minutes for DNS propagation
2. Visit: https://qamill.achieverthoughts.com
3. HTTPS: Auto-enabled by Netlify
4. All set! 🎉
```

---

### **If You Use: Vercel**

#### **Step 1: Deploy**
```
1. Git push website/ files to GitHub
2. Go to vercel.com
3. Import project from GitHub
4. Choose: website folder
5. Click Deploy
```

#### **Step 2: Custom Domain**
```
1. In Vercel Project Settings
2. Domains → Add Domain
3. Enter: qamill.achieverthoughts.com
4. Copy DNS records to your DNS provider
```

#### **Step 3: DNS Update**
```
Same as Netlify - add CNAME record to DNS:
Name: qamill
Type: CNAME
Value: cname.vercel-dns.com.
```

---

### **If You Use: AWS Amplify**

#### **Step 1: Deploy**
```
1. Connect GitHub repository
2. Build settings: website folder
3. Deploy
4. Get temporary domain
```

#### **Step 2: Custom Domain**
```
1. Domain Management → Add Domain
2. Enter: qamill.achieverthoughts.com
3. Amplify generates DNS records
4. Copy to DNS provider
```

---

### **If You Use: Cloudflare**

#### **Step 1: Prepare Files**
```
1. Upload website files to web server
   OR use Cloudflare Pages (recommended)
```

#### **Step 2: Create Subdomain (Via Cloudflare Pages)**
```
1. Login to Cloudflare
2. Pages → Create project
3. Connect GitHub with website/ files
4. Deploy
5. Add custom domain: qamill.achieverthoughts.com
```

#### **Step 3: Enable HTTPS**
```
1. SSL/TLS → Full (recommended)
2. Auto-renew enabled (default)
3. HTTPS: Automatic
```

---

## 🔧 Manual Upload (For Any Host)

If you prefer manual FTP upload:

```
Steps:
1. Get FTP credentials from hosting
2. Download FileZilla (free FTP client)
3. Connect to: ftp.achieverthoughts.com
4. Create folder: /public_html/qamill/
5. Drag website files:
   - index.html
   - styles.css
   - script.js
   - logo.svg (your logo)
   - hero-banner.png (your banner)

Verify:
- Visit: https://achieverthoughts.com/qamill
- All files present
- No 404 errors
- HTTPS working
```

---

## 📱 DNS Configuration

### **Common DNS Providers**

#### **GoDaddy**
```
1. Login to GoDaddy Account
2. Domains → Your domain → Manage DNS
3. Add new record:
   - Type: CNAME
   - Name: qamill
   - Value: (depends on your host)
4. Save
5. Wait 15-30 minutes for propagation
```

#### **Cloudflare**
```
1. Login to Cloudflare
2. DNS → Add record
3. Type: CNAME
4. Name: qamill
5. Target: (your host domain)
6. TTL: Auto
7. Proxy: DNS only (initially)
```

#### **Namecheap**
```
1. Dashboard → Domains → Manage
2. Advanced DNS
3. Add new record:
   - Type: CNAME Record
   - Host: qamill
   - Value: (your host)
   - TTL: 3600
4. Save
```

---

## ✅ Post-Deployment Checklist

After deployment, verify everything works:

```
□ Website loads: https://qamill.achieverthoughts.com
□ HTTPS working (no warnings)
□ Navigation links working
□ Slideshow functional:
  □ Next/Previous buttons
  □ Indicator dots clickable
  □ Arrow keys work
  □ Zoom in/out working
  □ Mobile swipe works
□ Mobile responsive:
  □ Desktop (1920px)
  □ Tablet (768px)
  □ Mobile (480px)
□ Images loading:
  □ Logo visible
  □ Hero banner visible
□ Contact links working
□ Performance acceptable:
  □ Load time < 3 seconds
  □ No console errors (F12)
□ SEO working:
  □ Title/description in browser tab
  □ Meta tags present
```

---

## 🚀 Quick Start (TL;DR)

**For most shared hosting (cPanel):**

```bash
1. SSH to server:
   ssh user@achieverthoughts.com

2. Create directory:
   mkdir -p public_html/qamill

3. Upload files:
   - Use FTP/SFTP
   - Or: git clone to folder

4. Set permissions:
   chmod 755 public_html/qamill
   chmod 644 public_html/qamill/*

5. Create .htaccess for HTTPS:
   nano public_html/qamill/.htaccess

6. Add:
   <IfModule mod_rewrite.c>
   RewriteEngine On
   RewriteCond %{HTTPS} off
   RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
   </IfModule>

7. Visit: https://achieverthoughts.com/qamill
```

---

## 🔐 Security Checklist

```
□ HTTPS enabled and enforced
□ No hardcoded API keys in code
□ No credentials in repository
□ robots.txt configured
□ Security headers set:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: SAMEORIGIN
  - Referrer-Policy: strict-origin
□ CSP header configured
□ No console errors
□ No mixed content warnings
```

---

## 📊 Monitoring

After deployment, monitor:

```
Google Analytics:
1. Add GA ID to index.html
2. Monitor traffic
3. Check slide engagement
4. Track CTA clicks

Uptime Monitoring:
1. Use UptimeRobot (free)
2. Monitor: https://qamill.achieverthoughts.com
3. Alert on downtime

Performance:
1. Google PageSpeed Insights
2. Check: Lighthouse score
3. Target: 90+ score
```

---

## 🎯 Integration with Main Site

### **Option A: Link from Main Homepage**
```html
<!-- Add to achieverthoughts.com home page -->
<a href="https://qamill.achieverthoughts.com" class="cta-button">
  Explore QAMill
</a>
```

### **Option B: Add to Navigation**
```html
<nav>
  <a href="https://achieverthoughts.com">Home</a>
  <a href="https://qamill.achieverthoughts.com">QAMill</a>
  <a href="https://achieverthoughts.com/about">About</a>
</nav>
```

### **Option C: Unified Footer**
```html
<!-- Footer on both sites -->
<footer>
  <a href="https://achieverthoughts.com">AchieverThoughts</a>
  <a href="https://qamill.achieverthoughts.com">QAMill</a>
  <a href="https://linkedin.com/company/achieverthoughts">LinkedIn</a>
</footer>
```

---

## 📞 Support Resources

### **DNS Propagation Checker**
- https://www.whatsmydns.net/

### **HTTPS Certificate Checker**
- https://www.sslshopper.com/ssl-checker.html

### **Website Speed Tester**
- https://pagespeed.web.dev/

### **Mobile Responsiveness Tester**
- https://search.google.com/test/mobile-friendly

---

## 🎉 You're All Set!

Your QAMill website is ready to integrate into achieverthoughts.com.

**Next Step:** Choose your hosting method from above and follow the appropriate guide.

Need help? The detailed instructions above cover all common hosting providers.

---

**Integration Complexity:** ⭐ Easy (5-15 minutes)  
**Time to Live:** 15-30 minutes (DNS propagation)  
**Status:** Ready to Deploy ✅
