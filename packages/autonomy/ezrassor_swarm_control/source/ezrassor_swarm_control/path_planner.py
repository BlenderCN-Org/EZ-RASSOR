#!/usr/bin/env python

import rospy

import sys
import numpy as np
import heapq
from PIL import Image
from timeit import default_timer as timer

from geometry_msgs.msg import Point
from ezrassor_swarm_control.msg import Path

import matplotlib.pyplot as plt


class PathPlanner:
    """
    Global A* path planner which runs on the gazebo world's height-map
    """

    def __init__(self, map_path, rover_max_climb_slope):

        # Read and store height-map
        self.map = np.array(Image.open(map_path), dtype=int)

        self.height, self.width = self.map.shape

        # Diagonals and cardinal direction movements allowed
        self.neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

        # Only cardinal directions
        # self.neighbors = [(0,1),(0,-1),(1,0),(-1,0)]

        # Maximum slope a rover can climb
        self.max_slope = rover_max_climb_slope

    def find_path(self, start, goal):
        """
        Leverages A* algorithm to find cost effective path from start to goal
        """

        if not self.check_bounds(start):
            rospy.loginfo('Start coordinate {} is out of bounds'.format((start.x, start.y)))
        if not self.check_bounds(goal):
            rospy.loginfo('Goal coordinate {} is out of bounds'.format((goal.x, goal.y)))

        rospy.loginfo('Searching for path from {} to {}'.format((start.x, start.y), (goal.x, goal.y)))
        start_time = timer()

        # Convert simulation coordinates, whose origin are in the center of the map,
        # to image coordinates with origin in the bottom-left corner
        start.x += self.width // 2
        start.y += self.height // 2
        goal.x += self.width // 2
        goal.y += self.height // 2

        # Initialize open and closed
        open = []
        closed = set()

        # These sets store the g and f values of each coordinate we'll visit
        g_scores = dict()
        f_scores = dict()

        previous = dict()

        # Initialize g and f for the start coordinate
        g_scores[start] = 0
        f_scores[start] = self.euclidean(start, goal)

        # Push start coord onto the open queue
        heapq.heappush(open, (f_scores[start], start))

        while open:
            # Visit coordinate with the smallest f value
            cur = heapq.heappop(open)[1]

            # Goal reached
            if cur == goal:

                # Build path by backtracking from current node to the start node
                path = self.backtrack_path(cur, start, previous)
                rospy.loginfo('Path found in {}'.format(timer() - start_time))
                plt.imshow(self.map)
                return path

            closed.add(cur)

            # Look at the current coordinate's neighbors
            neighbors = self.get_valid_neighbors(cur)

            for neighbor in neighbors:
                # Prevent illegal moves
                if not self.is_valid_move(cur, neighbor):
                    continue

                # Calculate new g value from current node
                tent_g = g_scores[cur] + self.euclidean(cur, neighbor)

                # No need to visit node if its already been visited
                # and the new g value isn't lower than the node's current g value
                if neighbor in closed and tent_g >= g_scores[neighbor]:
                    continue

                # Add node to open list if it hasn't been looked at or if
                # we've found a new cheaper path to this node
                if tent_g < g_scores.get(neighbor, sys.maxint) or neighbor not in [i[1] for i in open]:
                    previous[neighbor] = cur
                    g_scores[neighbor] = tent_g
                    f_scores[neighbor] = tent_g + self.euclidean(neighbor, goal)

                    heapq.heappush(open, (f_scores[neighbor], neighbor))

        print('No path found in {}'.format(timer() - start_time))
        return None

    def get_valid_neighbors(self, cur):
        '''
        Returns a list of valid neighboring nodes as ros Point messages
        '''

        neighbors = []

        for dx, dy in self.neighbors:
            x = cur.x + dx
            y = cur.y + dy

            # Check out of bounds neighbor
            if x < 0 or y < 0 or x >= self.width or y >= self.height:
                continue

            # Check if slope is too great between current and neighboring node
            if abs(self.map[y][x] - self.map[cur.y][cur.x]) > self.max_slope:
                continue

            neighbor = Point()
            neighbor.x = x
            neighbor.y = y
            neighbors.append(neighbor)

        return neighbors

    def is_valid_move(self, cur, neighbor):
        """
        Checks a move's edge cases such as moving in between or along base of a mountain or crater
        """

        dx = abs(cur.x - neighbor.x)
        dy = abs(cur.y - neighbor.y)

        # Diagonal move
        if dx == 1 and dy == 1:
            # Check for mountains or craters adjacent to diagonal move
            if abs(self.map[cur.y][neighbor.x] - self.map[cur.y][cur.x]) > 2 or \
                    abs(self.map[neighbor.y][cur.x] - self.map[cur.y][cur.x]) > 2:
                return False

        return True

    def backtrack_path(self, cur, start, previous):
        """
        Backtracks the path starting at the current node using the node's previous pointers
        """

        # Create path message
        p = Path()
        p.path = []

        while cur != start:
            # Convert image coordinates to gazebo simulation coordinates before adding to path
            cur.x -= self.width // 2
            cur.y -= self.width // 2

            p.path.append(cur)

            # Continue backtracking along each node's previous pointer
            if cur in previous:
                cur = previous[cur]
            else:
                raise ValueError('Unable to backtrack to start node.')

        # Reverse path before returning being that it's been built from goal to start
        p.path = p.path[::-1]
        return p

    def euclidean(self, a, b):
        """
        Returns the 3D euclidean distance between 2 ROS Points
        """

        # Difference in z value weighed heavily
        return np.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (self.map[b.y][b.x] - self.map[a.y][a.x]) ** 4)

    def check_bounds(self, coord):
        """
        Returns false if the given coordinate is out of bounds of the Gazebo world
        Gazebo coordinates have origin at 0,0
        """

        # Check x
        if coord.x < -self.width // 2 or coord.x > self.width // 2:
            return False

        # Check y
        if coord.y < -self.height // 2 or coord.y > self.height // 2:
            return False

        return True
