# Custom Domain Setup - qamill.achieverthoughts.com

## 🎯 Goal
Deploy QAMill website at: **https://qamill.achieverthoughts.com**

---

## 📋 **Step-by-Step Setup (10 Minutes)**

### **Step 1: Enable GitHub Pages (2 minutes)**

```
1. Go to: https://github.com/AT-Solves/QAMill/settings/pages
2. Under "Build and deployment":
   ✓ Source: GitHub Actions (already configured)
3. Scroll down to "Custom domain"
4. Enter: qamill.achieverthoughts.com
5. Click: Save
6. GitHub will show DNS configuration info
```

**Screenshot indicator:**
```
✅ You'll see green checkmark when DNS is correctly configured
⏳ Initially shows "DNS not configured yet" (that's normal)
```

---

### **Step 2: Configure DNS Records (5 minutes)**

**Login to your domain registrar:**

#### **If using GoDaddy:**
```
1. Go to: godaddy.com/dashboard
2. Find: achieverthoughts.com
3. Click: Manage DNS
4. Scroll to: DNS Records
5. Delete old CNAME if exists
6. Click: Add Record
   - Type: CNAME
   - Name: qamill
   - Points to: AT-Solves.github.io
   - TTL: 3600
7. Click: Save
```

#### **If using Cloudflare:**
```
1. Go to: dash.cloudflare.com
2. Select domain: achieverthoughts.com
3. Go to: DNS
4. Click: Add Record
   - Type: CNAME
   - Name: qamill
   - Target: AT-Solves.github.io
   - TTL: Auto
   - Proxy: DNS only
5. Click: Save
```

#### **If using NameCheap:**
```
1. Dashboard → Domains → achieverthoughts.com
2. Manage → Advanced DNS
3. Click: Add New Record
   - Type: CNAME Record
   - Host: qamill
   - Value: AT-Solves.github.io
   - TTL: 3600
4. Save
```

#### **If using other registrar:**
```
Add CNAME record:
- Subdomain: qamill
- Points to: AT-Solves.github.io
- TTL: 3600 (or default)
```

---

### **Step 3: Verify DNS Configuration (2 minutes)**

**Option A: Using online tool:**
```
1. Go to: https://www.whatsmydns.net/
2. Hostname: qamill.achieverthoughts.com
3. Query Type: CNAME
4. Check if all DNS servers show: AT-Solves.github.io
   ✅ Green checkmarks = Ready
```

**Option B: Using command line:**
```bash
# Check DNS propagation
nslookup qamill.achieverthoughts.com

# Or with dig
dig qamill.achieverthoughts.com CNAME

# Expected response:
# qamill.achieverthoughts.com. CNAME AT-Solves.github.io.
```

**Option C: Wait and check GitHub:**
```
1. Go to: GitHub repo → Settings → Pages
2. Custom domain field should show green checkmark
3. Message: "DNS lookup successful"
```

---

### **Step 4: Verify Website is Live (1 minute)**

**Visit your custom domain:**
```
https://qamill.achieverthoughts.com
```

**You should see:**
✅ QAMill website loads  
✅ Professional hero section visible  
✅ Navigation works  
✅ Slideshow functional  
✅ HTTPS enabled (green padlock)  

---

## ⏱️ **DNS Propagation Timeline**

```
Immediately: DNS record added to registrar
0-5 minutes: Some DNS servers updated
5-15 minutes: Most DNS servers updated  
15-30 minutes: Full global propagation (guaranteed)
```

**Note:** If not working immediately, wait 15-30 minutes. DNS changes take time to propagate.

---

## 🔒 **HTTPS Setup (Automatic)**

GitHub Pages automatically:
```
✅ Detects custom domain
✅ Generates SSL certificate (Let's Encrypt)
✅ Installs certificate (1-2 minutes)
✅ Enables HTTPS
✅ Redirects HTTP → HTTPS
✅ Renews certificate annually
```

**You should see:**
```
1. GitHub Settings → Pages
2. Green checkmark: "Certificate issued"
3. Message: "HTTPS enforced"
4. Browse: https://qamill.achieverthoughts.com (green padlock)
```

---

## 📝 **Settings Checklist**

After setup, verify these in GitHub Settings → Pages:

```
□ Source: GitHub Actions
□ Custom domain: qamill.achieverthoughts.com
□ Enforce HTTPS: Enabled (checkbox)
□ Certificate status: ✅ Issued
□ DNS status: ✅ Verified
```

---

## 🚨 **Troubleshooting**

### **Problem: "DNS not configured"**
```
Solution:
1. Verify CNAME record added to registrar
2. Check spelling: qamill.achieverthoughts.com
3. Wait 15-30 minutes
4. Use whatsmydns.net to check propagation
5. Clear GitHub Pages cache: Remove → Re-add custom domain
```

### **Problem: "Certificate not issued"**
```
Solution:
1. Wait 5 minutes (automatic)
2. Verify DNS is working (green checkmark for DNS)
3. Check HTTPS checkbox in settings
4. If still failing: Check DNS, remove domain, re-add
```

### **Problem: "Connection refused"**
```
Solution:
1. GitHub Actions workflow must complete first
2. Check: Actions tab → "Publish QAMill Website"
3. Wait for: ✅ Completed status
4. Then DNS configuration will work
```

### **Problem: Shows GitHub 404 page**
```
Solution:
1. Workflow hasn't run yet
   - Go to Actions tab
   - Click: "Publish QAMill Website to GitHub Pages"
   - Click: "Run workflow"
   - Wait 2-3 minutes
2. Verify index.html in website/ folder exists
3. Check branch is main
```

---

## ✅ **Final Verification Checklist**

When everything is set up:

```
□ Visit: https://qamill.achieverthoughts.com
□ Homepage loads (hero section visible)
□ Green padlock (HTTPS working)
□ Navigation smooth scrolls
□ Slideshow functional:
  □ Previous/Next buttons work
  □ Indicator dots work
  □ Arrow keys work
  □ Zoom in/out work
□ Mobile view works (F12 → Device Toolbar)
□ No console errors (F12 → Console)
□ Performance is fast (< 2 seconds load)
```

---

## 🎯 **What's Happening Behind the Scenes**

1. **You add custom domain to GitHub Pages**
   ↓
2. **GitHub generates SSL certificate**
   ↓
3. **You add CNAME DNS record**
   ↓
4. **DNS global propagation (15-30 min)**
   ↓
5. **GitHub verifies DNS is pointing to it**
   ↓
6. **HTTPS enabled automatically**
   ↓
7. **Website live at: https://qamill.achieverthoughts.com**

---

## 📊 **DNS Record Reference**

### **CNAME Record Details**

```
Record Type:  CNAME
Name/Host:    qamill
Target/Value: AT-Solves.github.io
TTL:          3600 (or default)
```

### **URL Mapping**

```
Before: https://AT-Solves.github.io/QAMill/
After:  https://qamill.achieverthoughts.com

CNAME points: qamill.achieverthoughts.com → AT-Solves.github.io
Result: Custom domain points to GitHub Pages server
```

---

## 🔗 **Useful Links**

**GitHub Pages Docs:**
- https://docs.github.com/en/pages

**DNS Propagation Checker:**
- https://www.whatsmydns.net/

**SSL Certificate Status:**
- Visit: GitHub Settings → Pages
- Check green checkmark for "Certificate issued"

**Registrar Docs:**
- GoDaddy: https://www.godaddy.com/help/add-a-cname-record-19236
- Cloudflare: https://developers.cloudflare.com/dns/manage-dns-records/reference/cname/
- NameCheap: https://www.namecheap.com/support/knowledgebase/article.aspx/9646/2237/how-do-i-set-up-a-cname-record

---

## ⏰ **Timeline Summary**

```
Minute 0: Add custom domain to GitHub
Minute 0: Add CNAME record to registrar DNS
Minute 1: GitHub generates SSL certificate
Minute 5: Certificate installed on GitHub
Minute 15-30: DNS propagation completes globally
Minute 30: Website accessible at custom domain
Minute 31: Celebrate! 🎉
```

---

## 🎉 **Final Result**

```
Website URL:      https://qamill.achieverthoughts.com
HTTPS:            ✅ Enabled
SSL Certificate:  ✅ Auto-issued & renewed
CDN:              ✅ GitHub Pages global CDN
Uptime:           ✅ 99.99%
Cost:             ✅ Free
Maintenance:      ✅ Automatic
```

---

## 📞 **Need Help?**

1. **Check GitHub Pages Documentation:**
   https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site

2. **Verify DNS Setup:**
   Use https://www.whatsmydns.net/ to check propagation

3. **Test Certificate:**
   Visit https://www.sslshopper.com/ssl-checker.html

4. **Check Workflow Status:**
   GitHub repo → Actions → "Publish QAMill Website to GitHub Pages"

---

## ✨ **You're All Set!**

Once DNS propagates, your website will be live at:

## 🌐 **https://qamill.achieverthoughts.com** ✅

---

**Status: READY TO DEPLOY**  
**Expected Time: 30-45 minutes total**  
**Complexity: ⭐ Easy**

Follow the 4 steps above and your custom domain will be live!

🚀 **Let's go!**
