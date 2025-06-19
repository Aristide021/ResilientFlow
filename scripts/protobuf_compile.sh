#!/bin/bash

# Protobuf Compilation Script for ResilientFlow
# Compiles the API protobuf definitions to Python

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"

echo "🔧 Compiling protobuf definitions..."

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc not found. Installing via package manager..."
    
    # Detect OS and install protoc
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y protobuf-compiler
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install protobuf
        else
            echo "❌ Homebrew not found. Please install protoc manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "❌ Please install protoc manually from https://github.com/protocolbuffers/protobuf/releases"
        exit 1
    else
        echo "❌ Unsupported OS: $OSTYPE"
        exit 1
    fi
fi

# Navigate to project root
cd "$PROJECT_ROOT"

# Create output directory if it doesn't exist
mkdir -p "$PROTO_DIR"

# Compile protobuf files
echo "📦 Compiling proto/api.proto..."

protoc \
    --python_out="$PROTO_DIR" \
    --proto_path="$PROTO_DIR" \
    "$PROTO_DIR/api.proto"

# Check if compilation was successful
if [[ -f "$PROTO_DIR/api_pb2.py" ]]; then
    echo "✅ Protobuf compilation successful!"
    echo "📁 Generated files:"
    echo "   - $PROTO_DIR/api_pb2.py"
else
    echo "❌ Protobuf compilation failed!"
    exit 1
fi

# Add __init__.py to make it a proper Python package
if [[ ! -f "$PROTO_DIR/__init__.py" ]]; then
    touch "$PROTO_DIR/__init__.py"
    echo "📦 Created $PROTO_DIR/__init__.py"
fi

# Optional: Install Python dependencies for protobuf
echo "🐍 Checking Python protobuf dependencies..."

if python3 -c "import google.protobuf" 2>/dev/null; then
    echo "✅ Python protobuf library is available"
else
    echo "⚠️  Python protobuf library not found. Installing..."
    pip3 install protobuf>=4.21.0
fi

echo ""
echo "🎉 Protobuf setup complete!"
echo ""
echo "💡 Usage in Python code:"
echo "   from proto import api_pb2"
echo "   event = api_pb2.DisasterEvent()"
echo "   event.event_id = 'hurricane_001'"
echo "" 