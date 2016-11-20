#!/usr/bin/env python
import rospy
import tf
import math
from geometry_msgs.msg import Twist, PoseStamped
from sl_crazyflie_msgs.msg import FlightMode, TargetMsg, ControlMode, Velocity
from tf import transformations
from sl_crazyflie_srvs.srv import ChangeFlightMode, ChangeFlightModeRequest, ChangeFlightModeResponse
from std_srvs.srv import Empty
import copy


def get_yaw_from_msg(msg):
    q = [msg.pose.orientation.x, msg.pose.orientation.y, msg.pose.orientation.z, msg.pose.orientation.w]
    euler = transformations.euler_from_quaternion(q)
    return euler[2]


def rotate_vector_by_angle(vector_x, vector_y, angle):
    x = vector_x * math.cos(angle) - vector_y * math.sin(angle)
    y = vector_x * math.sin(angle) + vector_y * math.cos(angle)

    return x, y

class GeoFenchingNode:
    def __init__(self):
        pose_topic = rospy.get_param("pose_topic", "/Robot_1/pose")
        vel_topic = rospy.get_param("vel_topic", "/geofencing/velocity")
        self.min_x = rospy.get_param("min_x", -1.2)
        self.min_y = rospy.get_param("min_y", -1.2)
        self.max_x = rospy.get_param("max_x", 0.1)
        self.max_y = rospy.get_param("max_y", 0.3)
        self.recover_speed = rospy.get_param("recover_speed", 0.3)
        self.buffer_len = rospy.get_param("buffer_len", 0.1)
        self.pose_sub = rospy.Subscriber(pose_topic, PoseStamped, self.callback_robot_pose)
        self.vel_pub = rospy.Publisher(vel_topic, Velocity)
        self.is_active = False

    def callback_robot_pose(self, pose):
        if not self.is_active and self.is_outside_fenc(pose):
            self.is_active = True

        if self.is_active and self.is_outside_fenc(pose, self.buffer_len):
            # calculate velocity
            # publish velocity
            self.calculate_velo(pose)
        else:
            self.is_active = False

    def calculate_velo(self, pose):

        velo = Velocity()
        if pose.pose.position.x < self.min_x + self.buffer_len:
            velo.x = self.recover_speed
        elif pose.pose.position.x > self.max_x - self.buffer_len:
            velo.x = -self.recover_speed

        if pose.pose.position.y < self.min_y + self.buffer_len:
            velo.y = self.recover_speed
        elif pose.pose.position.y > self.max_y - self.buffer_len:
            velo.y = -self.recover_speed

        norm = math.sqrt(velo.x**2 + velo.y**2)
        velo.x = velo.x / norm * self.recover_speed
        velo.y = velo.y / norm * self.recover_speed


        # toDo yaw
        current_yaw = get_yaw_from_msg(pose)
        rotation_angle = -current_yaw

        velo.x, velo.y = rotate_vector_by_angle(velo.x, velo.y, rotation_angle)
        self.vel_pub.publish(velo)


    def is_outside_fenc(self, pose, buffer=0.0):
        assert isinstance(pose, PoseStamped)
        return (pose.pose.position.x < self.min_x + buffer) or (pose.pose.position.y < self.min_y + buffer) or (
        pose.pose.position.x > self.max_x - buffer) or (pose.pose.position.y > self.max_y - buffer)


if __name__ == '__main__':
    rospy.init_node('GeoFenchingNode')
    manager = GeoFenchingNode()
    rate = rospy.Rate(3)
    while not rospy.is_shutdown():
        rate.sleep()
