#!/bin/bash
# Simplified CubeSat Deployment Script
# Lightweight implementation for easier deployment

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
COMPOSE_FILE="docker-compose.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Function to setup security keys automatically
setup_security() {
    print_status "Setting up security keys..."
    
    if [ -f "generate_keys.py" ]; then
        python3 generate_keys.py
        print_success "Security keys generated"
    else
        print_warning "generate_keys.py not found, skipping security setup"
    fi
}

# Function to build and deploy
deploy() {
    print_status "Starting simplified deployment..."
    
    # Setup security first
    setup_security
    
    # Build containers
    print_status "Building containers..."
    docker-compose -f "$COMPOSE_FILE" build --quiet
    print_success "Containers built"
    
    # Start services
    print_status "Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d
    sleep 5  # Brief wait for services to start
    
    # Show status
    print_status "Service status:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    print_success "Deployment completed successfully!"
    echo ""
    echo "Access the ground station at: http://localhost:8501"
    echo "Check logs with: ./deploy.sh logs"
}

# Function to stop services
stop() {
    print_status "Stopping services..."
    docker-compose -f "$COMPOSE_FILE" down
    print_success "Services stopped"
}

# Function to view logs
view_logs() {
    print_status "Showing logs..."
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    print_status "Current service status:"
    docker-compose -f "$COMPOSE_FILE" ps
}

# Function to run basic tests
run_tests() {
    print_status "Running basic tests..."
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_success "All services are running"
    else
        print_error "Some services are not running"
        docker-compose -f "$COMPOSE_FILE" ps
    fi
}

# Function to show help
show_help() {
    echo "Simplified CubeSat Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy the full system (default)"
    echo "  stop      Stop all services"
    echo "  status    Show current service status"
    echo "  logs      View service logs"
    echo "  test      Run basic system tests"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy    # Deploy the full system"
    echo "  $0 logs      # View service logs"
    echo "  $0           # Deploy the system (default)"
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        check_prerequisites
        deploy
        ;;
    stop)
        stop
        ;;
    status)
        show_status
        ;;
    logs)
        view_logs
        ;;
    test)
        run_tests
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac