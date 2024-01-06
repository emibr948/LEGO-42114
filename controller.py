import os
import time
import threading
#import numpy as np
from queue import Queue, Full
from enum import Enum
from pyPS4Controller.controller import Controller
from buildhat import Motor
from buildhat import Hat


class Actions(Enum):
    DRIVE = 1
    TURN = 2
    GEAR = 4
    TIPPING = 8
    KILL = 16


class Gears(Enum):
    UP = 16
    DOWN = 32
    TIPP = 64


class DumperController(Controller):

    def __init__(self, **kwargs):
        Controller.__init__(self, **kwargs)
        self.queue = None
        self.tipping = False

    def set_queue(self, que):
        self.queue = que

    def enqueue(self, data):
        """
        enqueue data to be saved
        :parameter
            data       (Tuple): (action, value)
        :return
            ret        (Boolean): queue full or not
        """
        if self.queue is None:
            return False

        ret = True
        try:
            self.queue.put(data, block=False)
        except Full:
            print(f"DumperController - enqueue full")
            ret = False
        return ret

    def on_square_press(self):
        pass

    def on_square_release(self):
        self.enqueue((Actions.GEAR, Gears.TIPP))

    def on_x_press(self):
        pass

    def on_x_release(self):
        self.enqueue((Actions.GEAR, Gears.DOWN))

    def on_triangle_press(self):
        pass

    def on_triangle_release(self):
        self.enqueue((Actions.GEAR, Gears.UP))

    def on_share_press(self):
        pass

    def on_share_release(self):
        print(list(self.queue.queue))

    # tipping up
    def on_up_arrow_press(self):
        if not self.tipping:
            self.enqueue((Actions.TIPPING, 1))
            self.tipping = True

    # tipping down
    def on_down_arrow_press(self):
        if not self.tipping:
            self.enqueue((Actions.TIPPING, -1))
            self.tipping = True

    def on_up_down_arrow_release(self):
        self.enqueue((Actions.TIPPING, 0))
        self.tipping = False

    # driving
    def on_L3_up(self, value):
        self.enqueue((Actions.DRIVE, value))

    def on_L3_down(self, value):
        self.enqueue((Actions.DRIVE, value))

    def on_R3_left(self, value):
        self.enqueue((Actions.TURN, value))

    def on_R3_right(self, value):
        self.enqueue((Actions.TURN, value))

    def on_R3_x_at_rest(self):
        self.enqueue((Actions.TURN, 0))

    def on_L3_y_at_rest(self):
        self.enqueue((Actions.DRIVE, 0))

    def on_options_press(self):
        self.enqueue((Actions.KILL, 0))


class DumperBrain(threading.Thread):

    def __init__(self, controller, num_cmds=10000):
        super(DumperBrain, self).__init__()
        self.queue = Queue(num_cmds)
        self.controller = controller
        self.controller.set_queue(self.queue)
        self.alive = True

        self.hat = Hat()
        self.active_gear = 2
        self.gears = [90, 0, -90, -135]
        self.turn_prev = 0
        self.turn_motor = Motor('A')
        self.drive_motor = Motor('B')
        self.gear_motor = Motor('C')
        self.turn_motor.plimit(1.0)
        self.drive_motor.plimit(1.0)
        self.gear_motor.plimit(1.0)
        self.start()

    def kill(self):
        self.alive = False

    def move_gear_motor(self, position):
        if self.drive_motor.get_speed() == 0:
            self.gear_motor.run_to_position(position, 100, True)
            return True
        return False

    def gear(self, value):
        if not self.drive_motor.get_speed() == 0:
            return False

        if value == Gears.TIPP and self.active_gear == 4:
            new_active_gear = 2
        elif value == Gears.TIPP and not self.active_gear == 4:
            new_active_gear = 4
        elif value == Gears.UP and not self.active_gear == 4:
            new_active_gear = self.active_gear + 1
            new_active_gear = min(new_active_gear, 3)
        elif value == Gears.DOWN and not self.active_gear == 4:
            new_active_gear = self.active_gear - 1
            new_active_gear = max(new_active_gear, 1)
        else:
            new_active_gear = self.active_gear

        if not new_active_gear == self.active_gear:
            self.move_gear_motor(0)
            self.move_gear_motor(self.gears[new_active_gear - 1])
            self.active_gear = new_active_gear
            print('active_gear', self.active_gear)

    def move_tipper(self, value):
        if value == 0:
            self.drive_motor.stop()
        else:
            self.drive_motor.start(value*100)

    def move_dumper(self, value):
        if value == 0:
            self.drive_motor.stop()
        else:
            self.drive_motor.start(int(0.003051*value))

    def turn_dumper(self, value):
        if value == 0:
            self.turn_motor.stop()
            #self.turn_motor.run_to_position(0, 100, False)
        else:
            print(int(0.003051*value))
            self.turn_motor.start(int(0.003051*value))

    def run(self):
        time_without_ca = 0
        while self.alive:
            while not self.queue.empty():
                action, value = self.queue.get(block=False, timeout=2)
                self.queue.task_done()

                # terminate
                if action == Actions.KILL:
                    self.move_gear_motor(0)
                    self.controller.stop = True
                    self.kill()
                if action == Actions.GEAR:
                    self.gear(value)
                if action == Actions.TIPPING and self.active_gear == 4:
                    self.move_tipper(value)
                if action == Actions.DRIVE and not self.active_gear == 4:
                    self.move_dumper(value)
                if action == Actions.TURN and not self.active_gear == 4:
                    self.turn_dumper(value)

                # print(action, value)
            
            # power monitoring    
            if self.hat.get_vin() < 7.0:
                self.hat.green_led(False)
                self.hat.orange_led(True)
            else:
                self.hat.green_led(True)
                self.hat.orange_led(False)
            
            time.sleep(0.01)

            # gear box idle position, also second gear when driving
            #time_without_ca += 0.01
            #if time_without_ca > 4.0:
            #    self.move_gear_motor(0)
            #    time_without_ca = 0.0


def main(args):
        controller = DumperController(interface="/dev/input/js0", connecting_using_ds4drv=False)
        brain = DumperBrain(controller)

        def terminate():
            brain.kill()
            brain.join()

        # you can start listening before controller is paired, as long as you pair it within the timeout window
        controller.listen(timeout=120, on_disconnect=terminate)


if __name__ == "__main__":
    main(None)
