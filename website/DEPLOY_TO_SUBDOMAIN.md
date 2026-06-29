# Deploy QAMill to qamill.achieverthoughts.com (Same Hosting)

**Goal:** Add qamill.achieverthoughts.com as subdomain on your existing achieverthoughts.com hosting

**No External Tools:** Just your hosting + FTP

---

## 🎯 **3 Simple Steps**

### **Step 1: Create Subdomain in cPanel (2 minutes)**

```
1. Login to cPanel: https://achieverthoughts.com:2083/
   (or your host's control panel)

2. Find: "Addon Domains" OR "Subdomains"

3. Click: "Create a New Subdomain"

4. Fill in:
   Subdomain: qamill
   Document Root: /public_html/qamill
   
5. Click: "Create"

✅ Subdomain qamill.achieverthoughts.com created
```

**If you can't find "Addon Domains":**
```
Look for: "Subdomains" in cPanel
Or: "Hosted Domains"
Or: Ask your hosting provider
```

---

### **Step 2: Create qamill Folder via FTP (1 minute)**

```
Using FileZilla or any FTP client:

1. Connect to: ftp.achieverthoughts.com
   Username: your cPanel username
   Password: your cPanel password
   Port: 21

2. Navigate to: /public_html/

3. Create new folder: qamill

4. Navigate into: /public_html/qamill/

✅ Folder ready for files
```

---

### **Step 3: Upload Website Files via FTP (2 minutes)**

```
Upload these files to /public_html/qamill/:
- index.html
- styles.css
- script.js

That's it! No other files needed.

Steps:
1. In FileZilla, right-click in qamill folder
2. Select: "Upload"
3. Choose files from: website/ folder locally
4. Drag & drop or click upload

✅ Files uploaded
```

---

## ✅ **Verify It Works**

```
1. Visit: https://qamill.achieverthoughts.com
2. You should see:
   ✅ QAMill hero section
   ✅ Professional styling
   ✅ Navigation working
   ✅ Slideshow working
   ✅ HTTPS with padlock (if already enabled)

3. If HTTPS not working yet:
   - cPanel → SSL/TLS
   - Install AutoSSL for qamill.achieverthoughts.com
   - Wait 5 minutes
   - Refresh browser
```

---

## 🔒 **Enable HTTPS (If Needed)**

```
If you see "Not Secure" warning:

1. Login to cPanel
2. Go to: SSL/TLS
3. Find: qamill.achieverthoughts.com
4. Click: "Install AutoSSL" OR "Install Let's Encrypt"
5. Wait 5 minutes
6. Clear browser cache (Ctrl+Shift+Delete)
7. Refresh page
✅ HTTPS enabled
```

---

## 📝 **Alternative: Using Command Line**

**If you have SSH access:**

```bash
# 1. SSH into your server
ssh user@achieverthoughts.com

# 2. Create folder
mkdir -p public_html/qamill

# 3. Upload files (from your local machine)
# Using SCP:
scp website/index.html user@achieverthoughts.com:public_html/qamill/
scp website/styles.css user@achieverthoughts.com:public_html/qamill/
scp website/script.js user@achieverthoughts.com:public_html/qamill/

# 4. Set permissions
ssh user@achieverthoughts.com
chmod 755 public_html/qamill
chmod 644 public_html/qamill/*

# 5. Done!
```

---

## 🎯 **Summary**

| Step | Method | Time | What to Do |
|------|--------|------|-----------|
| 1 | cPanel | 2 min | Create subdomain qamill |
| 2 | FTP | 1 min | Create /public_html/qamill/ folder |
| 3 | FTP | 2 min | Upload 3 files: HTML, CSS, JS |
| 4 | cPanel | 5 min | Enable HTTPS (AutoSSL) |
| 5 | Browser | 1 min | Visit & verify |
| **Total** | | **~11 min** | **Live!** |

---

## 📂 **File Structure After Upload**

```
Your Hosting Server:
public_html/
├── achieverthoughts.com files (existing)
└── qamill/
    ├── index.html        (from website/)
    ├── styles.css        (from website/)
    └── script.js         (from website/)
```

---

## 🔐 **Security Checklist**

```
✅ No API keys in code
✅ HTTPS enabled
✅ Proper file permissions
✅ No hardcoded passwords
✅ Static files only (safe)
```

---

## 🚨 **Common Issues & Fixes**

### **Issue: 404 Error (File Not Found)**

```
Cause: Files not in correct folder
Fix:
1. Verify files in: /public_html/qamill/
2. Filenames exactly: index.html, styles.css, script.js
3. Check FTP upload completed
```

### **Issue: Blank Page**

```
Cause: index.html not loading
Fix:
1. Check index.html is in /public_html/qamill/
2. Check spelling (case-sensitive on Linux servers)
3. Refresh page with Ctrl+Shift+R (hard refresh)
4. Check browser console (F12) for errors
```

### **Issue: Styling Not Applied**

```
Cause: CSS file path wrong
Fix:
1. Verify styles.css in same folder as index.html
2. In index.html, link should be: href="styles.css"
3. Not: href="/styles.css" or href="website/styles.css"
4. Hard refresh page
```

### **Issue: JavaScript Not Working**

```
Cause: JS file path wrong
Fix:
1. Verify script.js in same folder as index.html
2. In index.html, link should be: src="script.js"
3. Not: src="/script.js" or src="website/script.js"
4. Hard refresh page
5. Check console for errors (F12)
```

### **Issue: HTTPS Not Working**

```
Cause: SSL certificate not installed
Fix:
1. cPanel → SSL/TLS
2. Install AutoSSL for subdomain
3. Wait 5 minutes
4. Hard refresh page
5. Contact hosting if still failing
```

---

## 🔄 **Making Updates Later**

**To update the website:**

```
1. Update local files: website/ folder
2. Connect FTP to: /public_html/qamill/
3. Upload updated files
4. Replace existing files when prompted
5. Hard refresh in browser (Ctrl+Shift+R)
✅ Website updated!
```

---

## 📊 **What Files Go Where**

```
Do NOT create subdirectory:
❌ /public_html/qamill/website/ ← WRONG
❌ Files go: /public_html/qamill/website/index.html

Do create flat structure:
✅ /public_html/qamill/ ← CORRECT
✅ Files go: /public_html/qamill/index.html
✅ Files go: /public_html/qamill/styles.css
✅ Files go: /public_html/qamill/script.js
```

---

## 🎯 **Result**

After following these steps:

```
Website URL: https://qamill.achieverthoughts.com ✅
HTTPS: Enabled (green padlock)
Server: Your existing hosting ✅
No external tools: Just FTP + cPanel ✅
Cost: None (already paying for hosting)
Update: Simple FTP re-upload
```

---

## ✨ **Why This Works**

```
✅ Simple: 3 files, 1 folder
✅ No external services: Just your hosting
✅ No vendor lock-in: Files on your server
✅ Full control: You own everything
✅ Easy to update: FTP re-upload
✅ Cost: None (no additional services)
✅ Reliable: Same hosting as main site
✅ Performance: Shared hosting CDN/speed
```

---

## 📝 **FTP Client Recommendations**

**If you don't have an FTP client:**

```
Windows: FileZilla (free)
         WinSCP (free)
         
Mac:     Cyberduck (free)
         Transmit (paid)
         
Linux:   FileZilla (free)
         WinSCP (works in Wine)

Or use cPanel's built-in File Manager
(No FTP client needed if using cPanel's File Manager)
```

---

## 🔍 **Using cPanel File Manager (No FTP Needed)**

```
If your host has cPanel:

1. Login to cPanel
2. Find: "File Manager"
3. Click: public_html
4. Right-click: "Create New Folder"
5. Name: qamill
6. Enter folder, upload files

No FTP client needed!
```

---

## ⏱️ **Final Timeline**

```
Create subdomain:    2 minutes
Create folder:       1 minute
Upload files:        2 minutes
Enable HTTPS:        5 minutes (automatic)
Total setup:         ~10 minutes
Website live:        Immediate after upload ✅
```

---

## ✅ **Step-by-Step Checklist**

```
□ Have FTP credentials ready (or cPanel access)
□ Have your 3 website files ready:
  □ index.html
  □ styles.css
  □ script.js
□ Create subdomain in cPanel
□ Create /public_html/qamill/ folder
□ Upload 3 files to that folder
□ Enable HTTPS in cPanel
□ Visit: https://qamill.achieverthoughts.com
□ Verify website loads
□ Check: Navigation works
□ Check: Slideshow works
□ Check: Responsive on mobile
□ Done! ✅
```

---

## 🎉 **You're All Set!**

No external tools, no Netlify, no Vercel.

Just your hosting + FTP + cPanel.

**Simple, direct, and under your complete control.**

---

**Method: Direct FTP Upload**  
**Time: ~10 minutes**  
**Complexity: ⭐ Very Easy**  
**Cost: FREE (use your existing hosting)**  
**External Tools: NONE**  
**Result: https://qamill.achieverthoughts.com ✅**

🚀 **Let's deploy!**
