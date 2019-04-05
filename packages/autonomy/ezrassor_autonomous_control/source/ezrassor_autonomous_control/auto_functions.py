import rospy
import math
import utility_functions as uf
import nav_functions as nf

def at_target(world_state):
    """ Determine if the current position is within the desired threshold of the target position. """
    positionX = world_state.state_flags['positionX']
    positionY = world_state.state_flags['positionY']

    targetX = world_state.state_flags['target_location'][0]
    targetY = world_state.state_flags['target_location'][1]
    
    value = ((targetX - .5) < positionX < (targetX + .5) 
            and (targetY - .5) < positionY < (targetY + .5))

    return not value

def auto_drive_location(world_state, ros_util):
    """ Navigate to location. Avoid obstacles while moving toward location. """
    
    print("Auto Driving to {}".format(world_state.state_flags['target_location']))
    ros_util.status_pub.publish("Auto Driving to {}".format(world_state.state_flags['target_location']))
    
    # Main loop until location is reached
    while at_target(world_state):
        # Get new heading angle relative to current heading as (0,0)
        new_heading = nf.calculate_heading(world_state, ros_util)

        angle_difference = nf.adjust_angle(world_state.state_flags['heading'], new_heading)

        if angle_difference < 0:
            direction = 'right'
        else:
            direction = 'left'

        # Adjust heading until it matches new heading
        while not ((new_heading - 5) < world_state.state_flags['heading'] < (new_heading + 5)):
            ros_util.command_pub.publish(ros_util.commands[direction])
            ros_util.rate.sleep()
        
        # Avoid obstacles by turning left or right if warning flag is raised
        if world_state.state_flags['warning_flag'] == 1:
            uf.dodge_right(world_state, ros_util)
        if world_state.state_flags['warning_flag'] == 2:
            uf.dodge_left(world_state, ros_util)
        if world_state.state_flags['warning_flag'] == 3:
            uf.reverse_turn(world_state, ros_util)

        # Otherwise go forward
        ros_util.command_pub.publish(ros_util.commands['forward'])
            
        ros_util.rate.sleep()
    
    ros_util.command_pub.publish(ros_util.commands['null'])
        
def auto_dig(world_state, ros_util, duration):
    """ Rotate both drums inward and drive forward for duration time in seconds. """
    
    print("Auto Digging for {} Seconds".format(duration))
    ros_util.status_pub.publish("Auto Digging for {} Seconds".format(duration))

    uf.set_front_arm_angle(world_state, ros_util, -.1)
    uf.set_back_arm_angle(world_state, ros_util, -.1)

    combo_command = ros_util.commands['forward'] | ros_util.commands['front_dig'] | ros_util.commands['back_dig']
    
    # Perform Auto Dig for the desired Duration
    t = 0
    while t < duration*40:        
        ros_util.command_pub.publish(combo_command)
        t+=1
        ros_util.rate.sleep()


    uf.set_front_arm_angle(world_state, ros_util, 1.3)
    uf.set_back_arm_angle(world_state, ros_util, 1.3)

    ros_util.command_pub.publish(ros_util.commands['null'])

def auto_dock(world_state, ros_util):
    """ Dock with the hopper. """

    print("Auto Returning to {}".format([0,0]))
    ros_util.status_pub.publish("Auto Returning to {}".format([0,0]))

    world_state.state_flags['target_location'] = [0,0]
    auto_drive_location(world_state, ros_util)

def auto_dump(world_state, ros_util, duration):
    """ Rotate both drums inward and drive forward for duration time in seconds. """
    
    print("Auto Dumping")
    ros_util.status_pub.publish("Auto Dumping")
    
    t = 0
    while t < duration*40:        
        ros_util.command_pub.publish(ros_util.commands['front_dump'])
        t+=1
        ros_util.rate.sleep()
        t = 0

    new_heading = world_state.state_flags['heading'] = (world_state.state_flags['heading'] + 180) % 360

    while not ((new_heading - 1) < world_state.state_flags['heading'] < (new_heading + 1)):
            ros_util.command_pub.publish(ros_util.commands['left'])
            ros_util.rate.sleep()

    while t < duration*30:        
        ros_util.command_pub.publish(ros_util.commands['front_dump'])
        t+=1
        ros_util.rate.sleep()

    ros_util.command_pub.publish(ros_util.commands['null'])