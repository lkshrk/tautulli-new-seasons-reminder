#!/bin/bash
#
# Release script for tautulli-new-seasons-reminder
# Creates a git tag which triggers the release workflow
# Usage: ./scripts/release.sh v1.2.3
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Main script
main() {
    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ]; then
        log_error "pyproject.toml not found. Are you in the project root?"
        exit 1
    fi
    
    if [ ! -d "src/new_seasons_reminder" ]; then
        log_error "src/new_seasons_reminder not found. Are you in the project root?"
        exit 1
    fi
    
    # Check if git is clean
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "You have uncommitted changes. Please commit or stash them first."
        git status --short
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    if [ -z "$1" ]; then
        log_error "No version specified. Usage: $0 v1.2.3"
        exit 1
    fi
    
    # Validate version format
    if [[ ! "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Invalid version format. Use: v1.2.3"
        exit 1
    fi
    
    VERSION="$1"
    
    # Check if tag already exists
    if git rev-parse "$VERSION" >/dev/null 2>&1; then
        log_error "Tag $VERSION already exists"
        exit 1
    fi
    
    log_info "Creating git tag $VERSION..."
    git tag -a "$VERSION" -m "Release $VERSION"
    
    log_info "Pushing tag to remote..."
    git push origin "$VERSION"
    
    log_success "Release $VERSION created successfully!"
    log_info "GitHub Actions will now build and publish the release."
    log_info "Check the Actions tab in your GitHub repository for status."
}

# Run main function
main "$@"
