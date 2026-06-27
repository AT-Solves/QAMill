#!/bin/bash
# QAMill VSCode Extension - Marketplace Publishing Script
# Automates building and publishing to Visual Studio Marketplace

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXTENSION_DIR="vscode-extension"
PUBLISHER="achieverthoughts"
EXTENSION_NAME="qamill-mutation-testing"
VERSION="1.2.0"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   QAMill VSCode Extension - Marketplace Publisher          ║${NC}"
echo -e "${BLUE}║   Version: $VERSION                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print step
print_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
fi
print_success "Node.js found: $(node --version)"

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed"
fi
print_success "npm found: $(npm --version)"

if ! npm list -g vsce &> /dev/null; then
    print_error "vsce is not installed globally. Run: npm install -g vsce"
fi
print_success "vsce found: $(vsce --version)"

# Step 2: Check extension directory
print_step "Checking extension directory..."

if [ ! -d "$EXTENSION_DIR" ]; then
    print_error "Extension directory '$EXTENSION_DIR' not found"
fi
print_success "Extension directory found"

cd "$EXTENSION_DIR"

# Step 3: Verify package.json
print_step "Verifying package.json..."

if [ ! -f "package.json" ]; then
    print_error "package.json not found in $EXTENSION_DIR"
fi

CURRENT_VERSION=$(grep -m1 '"version"' package.json | awk -F'"' '{print $4}')
echo "Current version: $CURRENT_VERSION"

if [ "$CURRENT_VERSION" != "$VERSION" ]; then
    echo -e "${YELLOW}Warning: package.json version ($CURRENT_VERSION) != target version ($VERSION)${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Publishing cancelled"
    fi
fi
print_success "package.json verified"

# Step 4: Install dependencies
print_step "Installing dependencies..."
npm install 2>&1 | tail -5
print_success "Dependencies installed"

# Step 5: Compile TypeScript
print_step "Compiling TypeScript..."
npm run compile
if [ $? -eq 0 ]; then
    print_success "TypeScript compiled successfully"
else
    print_error "TypeScript compilation failed"
fi

# Step 6: Create VSIX package
print_step "Creating VSIX package..."
VSIX_FILE="${EXTENSION_NAME}-${VERSION}.vsix"

if [ -f "$VSIX_FILE" ]; then
    echo "Removing old VSIX: $VSIX_FILE"
    rm "$VSIX_FILE"
fi

vsce package --allow-missing-repository

if [ ! -f "$VSIX_FILE" ]; then
    print_error "VSIX package creation failed"
fi

VSIX_SIZE=$(ls -lh "$VSIX_FILE" | awk '{print $5}')
print_success "VSIX package created: $VSIX_FILE ($VSIX_SIZE)"

# Step 7: Verify VSIX contents
print_step "Verifying VSIX contents..."
MANIFEST_COUNT=$(unzip -l "$VSIX_FILE" | grep -c "package.json" || true)

if [ $MANIFEST_COUNT -eq 0 ]; then
    print_error "VSIX package is invalid (missing manifest)"
fi
print_success "VSIX package verified"

# Step 8: Ask for publication method
echo ""
echo -e "${BLUE}Publication Method:${NC}"
echo "1. Using stored PAT token (default)"
echo "2. Using custom PAT token"
echo "3. Manual upload (skip publishing)"
echo ""
read -p "Choose method (1-3): " -n 1 -r METHOD
echo ""

if [ -z "$METHOD" ]; then
    METHOD="1"
fi

case $METHOD in
    1)
        print_step "Publishing with stored token..."
        echo "Make sure you're logged in: vsce login $PUBLISHER"
        echo ""
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Publishing cancelled"
        fi

        vsce publish
        if [ $? -eq 0 ]; then
            print_success "Published successfully!"
        else
            print_error "Publishing failed"
        fi
        ;;
    2)
        print_step "Publishing with custom PAT token..."
        read -sp "Enter your PAT token: " PAT_TOKEN
        echo ""

        if [ -z "$PAT_TOKEN" ]; then
            print_error "PAT token cannot be empty"
        fi

        vsce publish -p "$PAT_TOKEN"
        if [ $? -eq 0 ]; then
            print_success "Published successfully!"
        else
            print_error "Publishing failed"
        fi
        ;;
    3)
        print_step "Skipping automatic publishing"
        echo ""
        echo "Manual upload instructions:"
        echo "1. Go to: https://marketplace.visualstudio.com/manage/publishers/$PUBLISHER"
        echo "2. Click on $EXTENSION_NAME"
        echo "3. Click 'New Release'"
        echo "4. Upload file: $VSIX_FILE"
        echo "5. Fill in release notes"
        echo "6. Publish"
        echo ""
        print_success "VSIX file ready for manual upload"
        ;;
    *)
        print_error "Invalid choice"
        ;;
esac

# Step 9: Marketplace verification
if [ "$METHOD" != "3" ]; then
    print_step "Verifying on Marketplace..."
    echo "Waiting 15 seconds for Marketplace to index..."
    sleep 15

    echo "Marketplace URL:"
    echo "https://marketplace.visualstudio.com/items?itemName=$PUBLISHER.$EXTENSION_NAME"
    echo ""
    echo "Installation command:"
    echo "code --install-extension $PUBLISHER.$EXTENSION_NAME"
fi

# Final summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   Publishing Complete! ✓                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Extension: $EXTENSION_NAME"
echo "Version: $VERSION"
echo "Publisher: $PUBLISHER"
echo "VSIX File: $VSIX_FILE"
echo ""
echo "Next steps:"
echo "1. Visit Marketplace to verify publication"
echo "2. Share extension link with your team"
echo "3. Monitor downloads and reviews"
echo "4. Respond to user feedback"
echo ""
