# QAMill Website - GitHub Pages Publishing Guide

## 🚀 Automatic Deployment via GitHub Actions

Your website automatically deploys to GitHub Pages whenever you push changes to the `website/` folder!

---

## 📍 GitHub Pages URL

```
https://AT-Solves.github.io/QAMill/
```

This URL is live immediately after pushing.

---

## ✅ How It Works

### **Automatic Publishing Process**

```
1. You push to main branch
2. GitHub Actions workflow triggers
3. Website files are built
4. Files uploaded to GitHub Pages
5. Website live at: https://AT-Solves.github.io/QAMill/
6. Takes ~2-3 minutes

All automatic - no manual steps needed!
```

### **Workflow File Location**
```
.github/workflows/publish-website.yml
```

---

## 🔧 Setup Requirements (One-Time)

### **Step 1: Enable GitHub Pages**

```
1. Go to: https://github.com/AT-Solves/QAMill
2. Settings → Pages
3. Build and deployment:
   - Source: GitHub Actions
   - (Automatically configured)
4. Save
```

### **Step 2: Verify Workflow**

```
1. Go to: Actions tab
2. Look for: "Publish QAMill Website to GitHub Pages"
3. Status should show: ✅ Completed
4. If not, run: workflow_dispatch (manual trigger)
```

### **Step 3: Test Deployment**

```
1. Visit: https://AT-Solves.github.io/QAMill/
2. Verify:
   ✅ Homepage loads
   ✅ Slideshow works
   ✅ Styling applied
   ✅ Images visible
```

---

## 🔄 Making Updates

### **Update Website Content**

```
1. Edit files in website/ folder:
   - index.html
   - styles.css
   - script.js

2. Commit changes:
   git add website/
   git commit -m "docs: Update website content"

3. Push to main:
   git push origin main

4. Workflow automatically runs
5. Website updates in ~2 minutes ✅
```

### **Add Custom Images**

```
1. Add your logo:
   website/logo.svg

2. Add hero banner:
   website/hero-banner.png

3. Commit:
   git add website/logo.svg website/hero-banner.png
   git commit -m "feat: Add QAMill branding images"

4. Push:
   git push origin main

5. Website updates automatically ✅
```

---

## 🌐 Custom Domain Setup

### **Connect qamill.achieverthoughts.com**

#### **Option A: GitHub Pages Custom Domain**

```
1. GitHub Settings → Pages
2. Custom domain: qamill.achieverthoughts.com
3. Copy DNS records shown
4. Go to your DNS provider (GoDaddy, Cloudflare, etc.)
5. Add CNAME record:
   - Name: qamill
   - Value: AT-Solves.github.io (or provided by GitHub)
   - TTL: 3600
6. Save and wait 15-30 minutes
7. Check "Enforce HTTPS" in GitHub Pages settings
8. Done! ✅
```

#### **Option B: Redirect from Main Site**

If you want to keep it on GitHub but link from your main site:

```html
<!-- Add to achieverthoughts.com -->
<a href="https://AT-Solves.github.io/QAMill/">
  Explore QAMill
</a>
```

---

## 📊 GitHub Pages Features

### **Automatic HTTPS**
```
✅ Free SSL/TLS certificate
✅ Auto-renewed
✅ No configuration needed
✅ Enforced with checkbox in settings
```

### **Performance**
```
✅ CDN-backed (fast worldwide)
✅ No server costs
✅ Unlimited bandwidth
✅ 1GB storage per repository
```

### **Custom Domain**
```
✅ Add custom domain (qamill.achieverthoughts.com)
✅ Auto-redirects HTTP → HTTPS
✅ CNAME record setup (simple)
✅ Works with any domain registrar
```

---

## 🔐 Security

GitHub Pages includes:
```
✅ HTTPS/TLS encryption
✅ DDoS protection
✅ Secure headers
✅ No server vulnerabilities
✅ GitHub infrastructure security
```

---

## 📈 Monitoring Deployment

### **Check Deployment Status**

```
1. Go to: Actions tab
2. Find: "Publish QAMill Website to GitHub Pages"
3. View status:
   ✅ In progress
   ✅ Completed successfully
   ❌ Failed (rare - check error logs)
```

### **View Deployment History**

```
1. Settings → Pages
2. Deployments section shows:
   - Each deployment timestamp
   - Success/failure status
   - Commit information
```

### **View Workflow Logs**

```
1. Actions tab
2. Click workflow run
3. View detailed logs:
   - Setup Pages
   - Upload artifacts
   - Deploy to Pages
```

---

## 🚨 Troubleshooting

### **Website Not Updating**

```
Problem: Changes pushed but not visible
Solution:
1. Verify workflow ran successfully (Actions tab)
2. Clear browser cache (Ctrl+Shift+Delete)
3. Hard refresh: Ctrl+Shift+R
4. Check URL: https://AT-Solves.github.io/QAMill/
5. Wait up to 5 minutes for propagation
```

### **HTTPS Not Working**

```
Problem: Browser shows insecure warning
Solution:
1. Settings → Pages
2. Check: "Enforce HTTPS" (enable if unchecked)
3. Wait 5 minutes for certificate
4. Refresh page
```

### **Custom Domain Not Working**

```
Problem: qamill.achieverthoughts.com shows error
Solution:
1. Verify DNS record added:
   - Type: CNAME
   - Value: AT-Solves.github.io
   - TTL: 3600
2. Wait 15-30 minutes for propagation
3. Check: whatsmydns.net
4. Re-enable GitHub Pages custom domain
5. Check: "Enforce HTTPS"
```

### **Images Not Loading**

```
Problem: Images appear broken
Solution:
1. Verify files uploaded to website/:
   - logo.svg
   - hero-banner.png
2. Check file paths in HTML are relative:
   - Good: ./logo.svg
   - Bad: /logo.svg or /website/logo.svg
3. Commit and push updated files
```

---

## 📋 Workflow File Details

### **What Does `publish-website.yml` Do?**

```yaml
Triggers:
  - Push to main branch
  - Changes in website/ folder
  - Manual trigger (workflow_dispatch)

Steps:
  1. Checkout code from GitHub
  2. Setup GitHub Pages environment
  3. Upload website/ folder as artifact
  4. Deploy artifact to GitHub Pages
  5. Report success with URL

Result:
  - Website live at: https://AT-Solves.github.io/QAMill/
  - Takes 2-3 minutes
  - HTTPS enabled automatically
```

---

## ✅ Pre-Publishing Checklist

Before your first publish:

```
□ Website files ready:
  □ index.html
  □ styles.css
  □ script.js
  □ DEPLOYMENT.md
  □ CUSTOM_DOMAIN_SETUP.md

□ Custom content added:
  □ logo.svg (your logo)
  □ hero-banner.png (your banner)

□ GitHub Actions enabled:
  □ Workflow file created (.github/workflows/publish-website.yml)
  □ Permission set to: GitHub Actions

□ GitHub Pages enabled:
  □ Settings → Pages
  □ Source: GitHub Actions
  □ HTTPS: Enforced (if using custom domain)

□ Testing before publish:
  □ Slideshow tested locally
  □ Zoom controls work
  □ Mobile responsive
  □ All links functional

□ Custom domain ready (optional):
  □ Domain registrar access
  □ DNS records ready to add
  □ Custom domain name
```

---

## 🎯 Publishing Workflow

### **First Publish**

```
1. Make sure website files are in place
2. Commit: git add website/
3. Commit: git commit -m "feat: Publish QAMill website"
4. Push: git push origin main
5. Go to Actions tab
6. Wait for workflow to complete (2-3 min)
7. Visit: https://AT-Solves.github.io/QAMill/
8. Celebrate! 🎉
```

### **Subsequent Updates**

```
1. Edit files in website/
2. Commit changes
3. Push to main
4. Workflow automatically runs
5. Website updates in ~2 minutes
6. No manual steps needed!
```

---

## 📊 Performance Stats

### **Deployment Time**
```
Checkout & setup:    ~30 seconds
Upload artifacts:    ~10 seconds
Deploy to Pages:     ~10 seconds
Total:              ~1-2 minutes
```

### **Website Performance**
```
Load time:          < 1 second (CDN)
HTTPS:              ✅ Included
Bandwidth:          ✅ Unlimited
Storage:            ✅ 1GB available
Availability:       ✅ 99.99%
```

---

## 🔗 Useful Links

**Current Deployment:**
```
https://AT-Solves.github.io/QAMill/
```

**GitHub Actions:**
```
https://github.com/AT-Solves/QAMill/actions
```

**GitHub Pages Settings:**
```
https://github.com/AT-Solves/QAMill/settings/pages
```

**Workflow File:**
```
.github/workflows/publish-website.yml
```

---

## 💡 Pro Tips

### **Faster Feedback Loop**
```
Edit → Commit → Push → Check Actions (2 min) → Live
Much faster than manual FTP uploads!
```

### **Version History**
```
Each GitHub release = website snapshot
Easy to rollback if needed
Git history = website history
```

### **Team Collaboration**
```
Multiple people can update website
All changes tracked in git
Comments on commits/PRs
```

### **Analytics & Monitoring**
```
Google Analytics: Add GA ID to index.html
Error tracking: Sentry or similar
Uptime monitoring: UptimeRobot
```

---

## 🎉 You're Live!

Your QAMill website is now publishing automatically to GitHub Pages.

**Every push to `website/` folder = automatic update**

```
1. Edit files
2. Commit
3. Push
4. Website updates automatically (2 minutes)
5. No additional steps needed!
```

---

## 📞 Support

For issues or questions:
- Check GitHub Actions tab for logs
- Review this guide's troubleshooting section
- Consult GitHub Pages docs: https://pages.github.com/

---

**Status: ✅ Live and Automated**

Your QAMill website is now published and will automatically update with every push!

🚀 **Happy publishing!**
