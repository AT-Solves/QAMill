# QAMill Team & Organization Sign-Up Guide

**Complete Guide to Individual, Team, and Organization Setup**

---

## 🎯 Sign-Up Options

QAMill supports **3 distinct sign-up flows** for different user types:

### **1. Individual Sign-Up** (Personal Account)
- Single user account
- Personal organization created automatically
- Full access to your own projects
- Can invite team members later

### **2. Team Sign-Up** (Invited Member)
- Invited via email by team lead or admin
- Join existing organization/team
- Role-based access (member, lead, admin)
- Collaborative access to shared projects

### **3. Organization Sign-Up** (Enterprise)
- Create organization for company/team
- Multi-team structure
- Role-based member management
- Centralized dashboards and reporting

---

## 👤 Individual Sign-Up

### **Step 1: Go to Sign-Up**

```
Visit: https://qamill.io/signup
Or: localhost:5173/signup
```

### **Step 2: Choose Sign-Up Method**

**Option A: Email & Password**
```
- Email: your.email@example.com
- Password: SecurePassword123!
- Name: Your Name
- Click "Create Account"
```

**Option B: OAuth (Single Sign-On)**
```
Click one of:
- "Sign up with Google"
- "Sign up with GitHub"
- "Sign up with Microsoft"
- "Sign up with LinkedIn"
- "Sign up with Slack"
- "Sign up with Atlassian"
```

### **Step 3: Verify Email**

```
1. Check your email
2. Click verification link
3. Account activated
4. Automatically logged in
```

### **Step 4: First Login**

```
Personal organization created:
- Organization: "Your Name's Organization"
- Role: Admin
- Projects: Empty
- Teams: None

Redirected to dashboard:
- Create project
- Invite team members
```

---

## 👥 Team Member Sign-Up

### **Scenario: Someone invites you to their team**

### **Step 1: Receive Invitation**

```
Email from: QAMill <noreply@qamill.io>

Subject: You're invited to join [Organization Name] on QAMill

Body:
  Hi John,
  
  Jane has invited you to join "Acme Corp" 
  on QAMill for test quality governance.
  
  Accept Invitation: [LINK]
  
  This invitation expires in 7 days.
```

### **Step 2: Click Invitation Link**

```
Link: https://qamill.io/invite/accept?token=xyz123...

Action:
- If logged in: Automatically join
- If not logged in: Go to sign-up
```

### **Step 3: Create Account (if needed)**

```
If you don't have account yet:
1. Click "Create Account"
2. Enter email (pre-filled from invite)
3. Enter password
4. Click "Accept Invitation"
```

### **Step 4: Join Organization**

```
Confirmation:
✅ You've joined "Acme Corp"!

Your role: Member
├─ Full project access
├─ Can create analyses
├─ Can contribute
└─ Cannot manage members

Redirected to: Organization dashboard
├─ See organization projects
├─ See team members
└─ Start analyzing
```

---

## 🏢 Organization Sign-Up (Enterprise)

### **Scenario: Your company wants to use QAMill**

### **Step 1: Organization Sign-Up**

```
Go to: https://qamill.io/org/signup

Fill in:
- Organization Name: "Acme Corporation"
- Description: "Quality Assurance Team"
- Your Email: admin@acme.com
- Your Name: Jane Smith
- Website: www.acme.com (optional)
- Logo: [Upload] (optional)

Click: "Create Organization"
```

### **Step 2: Account Setup**

```
Automatically created:
- User account: admin@acme.com
- Organization: "Acme Corporation"
- Your role: Admin
- Personal team: Created
```

### **Step 3: Organization Created**

```
Confirmation:
✅ "Acme Corporation" organization created!

You are: Organization Admin
├─ Create/delete teams
├─ Manage members
├─ Configure settings
├─ View all projects
└─ Generate reports

Redirected to: Organization Admin Dashboard
```

---

## 🤝 Managing Your Organization

### **Create a Team**

```
1. Go to: Organization > Teams
2. Click: "Create Team"
3. Fill in:
   - Team Name: "QA Testing"
   - Description: "Test automation team"
4. Click: "Create"

Result:
✅ Team created
├─ Team ID: team_0001
├─ Created by: You
└─ Members: Just you
```

### **Invite Team Members**

#### **Method 1: Email Invitation**

```
1. Go to: Team > Members
2. Click: "Invite Member"
3. Fill in:
   - Email: team.member@acme.com
   - Role: Member (or Lead/Viewer)
   - Send as: Invite link
4. Click: "Send Invitation"

Action:
- Email sent to team.member@acme.com
- Valid for 7 days
- Can accept anytime
```

#### **Method 2: Add Existing User**

```
1. Go to: Team > Members
2. Click: "Add Member"
3. Select: Existing user from org
4. Set Role: Member/Lead/Admin
5. Click: "Add"

Result:
✅ User added immediately
├─ Can access team projects
├─ Can collaborate
└─ Notifications sent
```

### **Manage Member Roles**

```
Roles Available:

1. Admin (Organization only)
   - Manage all members
   - Create/delete teams
   - View all projects
   - Configure organization

2. Lead (Team level)
   - Manage team members
   - Create projects
   - Full access to team projects
   - Delegate work

3. Member
   - Create analyses
   - View projects
   - Contribute to projects
   - Cannot invite members

4. Viewer
   - Read-only access
   - View reports
   - View analyses
   - Cannot edit/create
```

---

## 📊 Multi-Level Access

### **Organization Hierarchy**

```
Organization (Acme Corp)
├── Admin: Jane Smith
│   ├── Can manage all teams
│   ├── Can invite org members
│   └── Can view all projects
│
├── Team 1: QA Testing
│   ├── Lead: John Doe
│   ├── Member: Alice Johnson
│   ├── Member: Bob Williams
│   └── Viewer: Contract QA
│
└── Team 2: Performance Testing
    ├── Lead: Carol Davis
    ├── Member: Dave Martinez
    └── Member: Eve Anderson
```

### **Access Examples**

**Jane (Org Admin)**
- Can see all projects
- Can invite anyone to org
- Can create new teams
- Can manage all members
- Can view all analyses

**John (Team Lead)**
- Can see QA Testing projects
- Can invite to QA Testing team
- Can manage QA team members
- Can create projects
- Can delegate tasks

**Alice (Team Member)**
- Can see QA Testing projects
- Can create analyses
- Can contribute to discussions
- Cannot invite members
- Cannot manage team

**Contract QA (Viewer)**
- Can read reports
- Can view analyses
- Can see results
- Cannot create/edit
- Cannot invite
- Cannot manage

---

## 📧 Shared Project Access

### **Share Project with Team**

```
1. Project Owner > Settings
2. Click: "Share"
3. Select: Team to share with
4. Confirm: "Share with QA Team"

Result:
✅ All team members can:
├─ View project
├─ See analyses
├─ Download reports
└─ (Per their role)
```

### **Share Analysis with Organization**

```
1. Analysis > Share
2. Select: Organization "Acme Corp"
3. Confirm sharing

Result:
✅ All org members can:
├─ View analysis
├─ Download report
├─ See metrics
└─ (Per their role)
```

---

## 🔐 Security & Permissions

### **Access Control**

```
All endpoints check:
1. User is authenticated
2. User belongs to org/team
3. User has required role
4. Project is accessible to user

Request fails if:
- User not authenticated
- User not in organization
- User role insufficient
- Project not shared
```

### **Invitation Security**

```
Invitations use:
- Unique secure tokens
- Email verification
- 7-day expiration
- One-time acceptance
- Revocable at any time
```

### **Session Security**

```
User sessions:
- JWT token-based
- 30-day expiration
- Refresh token support
- Multi-device support
- Logout revokes all
```

---

## 📱 User Workflows

### **Workflow 1: Solo Developer**

```
1. Sign up individually
2. Personal org created
3. Create project
4. Run analysis
5. View report
6. Done!
```

### **Workflow 2: Team Collaboration**

```
1. Admin creates organization
2. Admin creates teams
3. Admin invites members
4. Members accept invitations
5. Create shared projects
6. Run analyses together
7. Share reports
8. Collaborate on improvements
```

### **Workflow 3: Enterprise Deployment**

```
1. IT admin creates org
2. Creates departments as teams
3. Bulk invites employees
4. Employees accept
5. Department teams created
6. Projects shared by department
7. Centralized reporting
8. Executive dashboards
9. Cross-team collaboration
```

---

## 🎯 Roles & Permissions Matrix

| Action | Admin | Lead | Member | Viewer |
|--------|-------|------|--------|--------|
| Create Project | ✅ | ✅ | ✅ | ❌ |
| Edit Project | ✅ | ✅ | ✅ | ❌ |
| Run Analysis | ✅ | ✅ | ✅ | ❌ |
| View Report | ✅ | ✅ | ✅ | ✅ |
| Download Report | ✅ | ✅ | ✅ | ✅ |
| Share Project | ✅ | ✅ | ❌ | ❌ |
| Invite Member | ✅ | ✅ | ❌ | ❌ |
| Manage Members | ✅ | ✅ | ❌ | ❌ |
| Create Team | ✅ | ❌ | ❌ | ❌ |
| Delete Project | ✅ | ✅ | ❌ | ❌ |
| View Org Settings | ✅ | ❌ | ❌ | ❌ |

---

## 💡 Best Practices

### **For Organization Admins**

1. **Create teams by department** - QA, Backend, Frontend
2. **Use appropriate roles** - Don't make everyone admin
3. **Regular member audits** - Remove old members
4. **Share strategically** - By team, not broadcast
5. **Backup reports** - Download important analyses

### **For Team Leads**

1. **Onboard new members** - Welcome and brief
2. **Delegate appropriately** - Match roles to skills
3. **Regular check-ins** - Review metrics together
4. **Share knowledge** - Cross-team learnings
5. **Document standards** - Test quality expectations

### **For Team Members**

1. **Set up notifications** - Get alerts on shares
2. **Review regularly** - Check team analyses
3. **Contribute ideas** - Suggest improvements
4. **Document findings** - Share discoveries
5. **Support teammates** - Help improve together

---

## ❓ FAQ

**Q: Can I have multiple organizations?**
A: Yes! You can be admin of one, member of others.

**Q: How do I leave a team?**
A: Go to Team > Members > Remove yourself.

**Q: Can I invite external contractors?**
A: Yes, invite with Viewer role for limited access.

**Q: What if invitation expires?**
A: Admin can resend it or create new one.

**Q: Can I change member roles?**
A: Yes, as Admin or Team Lead.

**Q: How long do invitations last?**
A: 7 days, then automatically expire.

**Q: Can I delete an organization?**
A: Yes, if you're the admin. This removes all teams and projects.

**Q: What happens to projects if team is deleted?**
A: Projects can be transferred to another team or archived.

---

## 🚀 Getting Started

### **Choose Your Path:**

**Path 1: Individual User**
```
1. Go to https://qamill.io
2. Click "Sign Up"
3. Email or OAuth
4. Create first project
5. Run analysis
→ Takes 5 minutes!
```

**Path 2: Team Member**
```
1. Receive email invitation
2. Click link in email
3. Create account (if needed)
4. Accept invitation
5. You're in!
→ Takes 2 minutes!
```

**Path 3: Organization**
```
1. Go to https://qamill.io/org/signup
2. Fill organization info
3. Create account
4. Confirm email
5. Create teams
6. Invite members
→ Takes 10 minutes to start!
```

---

## ✅ Summary

QAMill supports **3 sign-up flows**:

✅ **Individual** - Personal org, full control
✅ **Team Member** - Invited, role-based access  
✅ **Organization** - Multi-team, enterprise ready

All with:
- 🔐 Secure authentication (email + OAuth)
- 👥 Role-based access control
- 📧 Email invitations
- 🔗 Project sharing
- 📊 Multi-level dashboards
- 🎯 Collaborative workflows

**Get started now at:** https://qamill.io 🚀
