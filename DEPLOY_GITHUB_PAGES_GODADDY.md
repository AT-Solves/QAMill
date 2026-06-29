# Deploy QAMill to qamill.achieverthoughts.com
## GitHub Pages + GoDaddy DNS Configuration

**Total Time: 20-30 minutes**  
**Complexity: ⭐ Easy**  
**No FTP needed | No server access needed**

---

## 🎯 **What You'll Do**

```
1. Enable GitHub Pages in repository (2 min)
2. Add DNS record in GoDaddy (5 min)
3. Configure custom domain in GitHub (2 min)
4. Wait for DNS to propagate (15 min)
5. Visit website at qamill.achieverthoughts.com ✅
```

---

## ✅ **Step 1: Enable GitHub Pages (2 minutes)**

### **1.1 Go to Repository Settings**

```
Open: https://github.com/AT-Solves/QAMill/settings/pages
```

### **1.2 Configure Build Source**

```
Under "Build and deployment":

Current Source: (may show different option)
Change to: GitHub Actions

Click: Save
```

**What you'll see:**
```
✓ "Build and deployment" section visible
✓ Source dropdown showing options
✓ "GitHub Actions" option available
```

### **1.3 Wait for Workflow**

```
Go to: Actions tab (in your repo)
Find: "Publish QAMill Website to GitHub Pages"
Watch status: In progress → Completed (2-3 minutes)
```

**When complete, you'll see:**
```
✅ Green checkmark next to workflow name
✅ Message shows deployment successful
```

---

## 🌐 **Step 2: Add DNS Record in GoDaddy (5 minutes)**

### **2.1 Log into GoDaddy**

```
Go to: https://www.godaddy.com/
Click: Account (top right)
Sign in with your credentials
```

### **2.2 Find Your Domain**

```
Left sidebar: Find "Domains"
Find: achieverthoughts.com
Click on it
```

### **2.3 Go to DNS Settings**

```
In achieverthoughts.com settings:
Look for: "DNS" or "Manage DNS"
Click: "Manage DNS" or "DNS Settings"

You should see a list of existing DNS records
```

### **2.4 Add New CNAME Record**

```
Look for: "Add Record" or "+" button
Click it

Fill in:
┌─────────────────────────────────────┐
│ Type: CNAME                         │
│ Name: qamill                        │
│ Points to: AT-Solves.github.io     │
│ TTL: 3600 (or default)             │
└─────────────────────────────────────┘

Click: Save or Add Record
```

**IMPORTANT:** 
```
❌ Do NOT add: qamill.achieverthoughts.com
✅ Only add: qamill (GoDaddy adds the domain automatically)
```

**Screenshot reference:**
```
Your DNS records will look like:
┌─────────────────────────────────────┐
│ Type | Name  | Points To           │
├─────────────────────────────────────┤
│ A    | @     | 173.x.x.x          │ (existing)
│ MX   | @     | aspmx.l.google...  │ (existing)
│ ...  | ...   | ...                 │
│ CNAME| qamill| AT-Solves.github.io│ (NEW - add this)
└─────────────────────────────────────┘
```

### **2.5 Verify DNS Record Added**

```
After saving, you should see:
Type: CNAME
Name: qamill
Target: AT-Solves.github.io
TTL: 3600

If you see this, you're done with GoDaddy! ✅
```

---

## 📍 **Step 3: Configure Custom Domain in GitHub (2 minutes)**

### **3.1 Go Back to GitHub Pages Settings**

```
Open: https://github.com/AT-Solves/QAMill/settings/pages
(Same page as Step 1)
```

### **3.2 Add Custom Domain**

```
Look for: "Custom domain" field
(Should be below the Build and deployment section)

Enter: qamill.achieverthoughts.com
Click: Save
```

**What you'll see:**
```
First: ⏳ "DNS lookup in progress..."
Then: ✅ "Your site is published at https://qamill.achieverthoughts.com"
      OR
      ⏳ "DNS is not configured yet" (this is OK, wait)
```

### **3.3 Enable HTTPS**

```
Scroll down in same page
Look for: "Enforce HTTPS" checkbox
Check it: ✓ Enforce HTTPS

(GitHub will automatically get SSL certificate)
```

**When complete:**
```
✅ "Certificate issued" message appears
✅ "HTTPS enforced" shows as enabled
```

---

## ⏱️ **Step 4: Wait for DNS Propagation (15 minutes)**

```
DNS changes take time to spread globally

Timeline:
0-5 min:    Some servers updated
5-15 min:   Most servers updated
15-30 min:  All servers updated (guaranteed)

During this time:
- GitHub Pages settings may show "DNS not verified yet"
- This is NORMAL
- Keep waiting

Refresh GitHub Pages settings every 5 minutes to check status
```

---

## ✅ **Step 5: Verify Website is Live**

### **5.1 Visit Your Website**

```
Open browser, go to:
https://qamill.achieverthoughts.com
```

### **5.2 Check These Things**

```
✅ Page loads (doesn't show 404 error)
✅ Green padlock icon (HTTPS working)
✅ See QAMill hero section
✅ Navigation menu visible
✅ Slideshow appears
✅ Mobile view works (try zooming out)
```

### **5.3 Test Functionality**

```
✅ Click navigation links - smooth scroll
✅ Slideshow: Click next/previous buttons
✅ Slideshow: Click indicator dots
✅ Zoom: Click + and - buttons
✅ Mobile: Press F12, toggle mobile view
```

---

## 🔍 **Troubleshooting**

### **Issue 1: Still shows 404 error after 30 minutes**

```
Solution:
1. GitHub Pages settings → Check Source is "GitHub Actions"
2. Go to Actions tab → Check workflow completed ✅
3. GoDaddy DNS → Verify CNAME record exists:
   - Type: CNAME
   - Name: qamill
   - Target: AT-Solves.github.io
4. Use https://www.whatsmydns.net/ to check DNS:
   - Enter: qamill.achieverthoughts.com
   - Should show: AT-Solves.github.io in all entries
5. Clear browser cache (Ctrl+Shift+Delete) and hard refresh
```

### **Issue 2: HTTPS shows certificate warning**

```
Solution:
1. GitHub Pages settings → Check "Enforce HTTPS" is checked
2. Wait 5 more minutes for certificate installation
3. Hard refresh page (Ctrl+Shift+R)
4. Try again
```

### **Issue 3: Website shows GitHub 404 page**

```
Solution:
1. Check Actions tab → Workflow shows "completed" ✅
2. If workflow failed, it will show ❌ error
3. Check GitHub Pages settings → Source: GitHub Actions
4. Website files exist in website/ folder
5. index.html must be in website/ folder
```

### **Issue 4: Pages shows "Custom domain not verified"**

```
This is normal while DNS propagates
Wait 15-30 minutes and refresh the page
When DNS propagates, it will automatically verify
```

---

## 📊 **Expected Timeline**

```
Action                              Time
─────────────────────────────────────────
1. Enable GitHub Pages              2 min
2. Workflow runs                     2 min
3. Add DNS record in GoDaddy        5 min
4. Configure custom domain in GitHub 2 min
5. DNS global propagation           15 min
6. Website live                     1 min (verification)
─────────────────────────────────────────
TOTAL                              27 min
```

---

## ✨ **What's Happening**

```
Step 1-2: GitHub Pages gets your website ready
          Website lives at: AT-Solves.github.io/QAMill/

Step 3: You tell GoDaddy where qamill points to
        GoDaddy: qamill → AT-Solves.github.io

Step 4: You tell GitHub to use your custom domain
        GitHub: Use qamill.achieverthoughts.com

Step 5: DNS propagates globally
        All servers learn: qamill.achieverthoughts.com → GitHub Pages

Result: When someone visits qamill.achieverthoughts.com
        → GoDaddy DNS directs them to GitHub Pages
        → GitHub Pages serves your website ✅
```

---

## 🔒 **Security & HTTPS**

```
✅ HTTPS is automatic (Let's Encrypt)
✅ Certificate auto-renews
✅ No manual setup needed
✅ Your data is encrypted
✅ Green padlock visible
```

---

## 📋 **Complete Checklist**

### **GitHub Setup**
```
□ Go to: https://github.com/AT-Solves/QAMill/settings/pages
□ Source: Select "GitHub Actions"
□ Click: Save
□ Go to: Actions tab
□ Verify: Workflow shows ✅ Completed
□ Go back to: Pages settings
□ Add custom domain: qamill.achieverthoughts.com
□ Click: Save
□ Check: "Enforce HTTPS" is checked
```

### **GoDaddy Setup**
```
□ Login to: GoDaddy
□ Find: achieverthoughts.com
□ Go to: DNS Settings
□ Add CNAME record:
  □ Type: CNAME
  □ Name: qamill
  □ Points to: AT-Solves.github.io
□ Save
□ Verify record appears in list
```

### **Verification**
```
□ Wait 15-30 minutes
□ Open: https://qamill.achieverthoughts.com
□ See: QAMill website loads
□ See: Green padlock (HTTPS)
□ Test: Navigation works
□ Test: Slideshow works
□ Test: Mobile view works
□ Done! ✅
```

---

## 🎯 **Quick Reference**

**GoDaddy DNS Record to Add:**
```
Type:        CNAME
Name:        qamill
Points to:   AT-Solves.github.io
TTL:         3600
```

**GitHub Pages Settings:**
```
Build and deployment → Source: GitHub Actions
Custom domain: qamill.achieverthoughts.com
Enforce HTTPS: ✓ Checked
```

**Final Website URL:**
```
https://qamill.achieverthoughts.com
```

---

## ✅ **You're All Set!**

Everything is ready. Just follow these 5 steps and your website will be live!

**Questions?** Refer back to the troubleshooting section or reread the step that's confusing.

---

## 🚀 **Ready? Start with Step 1!**

Go to: https://github.com/AT-Solves/QAMill/settings/pages

**Let's get qamill.achieverthoughts.com live!** 🎉
