#!/usr/bin/env python
"""Listen for and route POST requests to the ROS graph's requests topic.

The HTTP server will not stop until a final POST request is received after
ROS has shut down.
Written by Tiger Sachse.
"""
import json
import rospy
import httplib
import std_msgs
import BaseHTTPServer


PORT = 8080
QUEUE_SIZE = 10
NODE_NAME = "http_server"
REQUESTS_TOPIC = "/ezrassor/requests"


def get_custom_handler(requests_publisher):
    """Return a custom request handler with an embedded ROS publisher."""

    class CustomRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        """Handle POST requests on a simple HTTP server."""
        publisher = requests_publisher

        def do_POST(self):
            """Handle all POST requests."""
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            content_length = int(self.headers.getheader("content-length", 0))
            body = self.rfile.read(content_length)
            self.publisher.publish(int(body))
            self.wfile.write(json.dumps({"status" : 200}))

    return CustomRequestHandler


# Entry point to this node.
try:
    rospy.init_node(NODE_NAME)
    requests_publisher = rospy.Publisher(REQUESTS_TOPIC,
                                         std_msgs.msg.Int16,
                                         queue_size=QUEUE_SIZE)
    
    # Create an HTTP server.
    server = BaseHTTPServer.HTTPServer(("", PORT),
                                       get_custom_handler(requests_publisher))

    # Check for server requests while ROS is running.
    while not rospy.core.is_shutdown():
        server.handle_request()
except rospy.ROSInterruptException:
    pass
