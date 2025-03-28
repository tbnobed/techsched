from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health_check():
    """
    Health check endpoint for monitoring and Docker healthchecks.
    Returns a 200 status code with a simple JSON response.
    """
    return jsonify({"status": "healthy"})