#!/bin/bash
# Setup script for job automation system

set -e

echo "🚀 Setting up Job Automation System"
echo "===================================="

# Check requirements
echo ""
echo "Checking requirements..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

echo "✓ Python $(python3 --version)"
echo "✓ Node $(node --version)"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Install Node dependencies
echo ""
echo "Installing Node.js dependencies..."
npm install

# Initialize data files
echo ""
echo "Initializing data files..."

cat > data/jobs.json << EOF
{
  "jobs": [],
  "last_updated": null
}
EOF

cat > data/applied.json << EOF
{
  "applications": []
}
EOF

echo "✓ Created data/jobs.json"
echo "✓ Created data/applied.json"

# Make scripts executable
chmod +x scripts/*.py scripts/*.js

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Set up GitHub repository and enable Actions"
echo "2. Add ANTHROPIC_API_KEY to GitHub Secrets"
echo "3. Customize config.yml with your job search parameters"
echo "4. Test locally: python3 scripts/scrape_jobs.py"
echo ""
echo "See README.md for detailed usage instructions."
