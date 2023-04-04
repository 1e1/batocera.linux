import batoceraFiles
import Command
import controllersConfig
from generators.Generator import Generator
import os
import shlex

class GZDoomGenerator(Generator):
    def generate(self, system, rom, playersControllers, guns, gameResolution):
        config_dir = f"{batoceraFiles.CONF}/gzdoom"
        ini_file = config_dir + "/gzdoom.ini"

        # check the path is added to the ini file
        fm_banks = "Path=/userdata/system/configs/gzdoom/fm_banks\n"
        sound_fonts = "Path=/userdata/system/configs/gzdoom/soundfonts\n"
        
        # check directories exist
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)
        if not os.path.exists(config_dir + "/soundfonts"):
            os.mkdir(config_dir + "/soundfonts")
        if not os.path.exists(config_dir + "/fm_banks"):
            os.mkdir(config_dir + "/fm_banks")

        have_gles = os.path.exists("/usr/lib/libGLESv2_CM.so") or os.path.exists("/usr/lib/libGLESv2.so")
        have_opengl = os.path.exists("/usr/lib/libGL.so")

        extra_config = ""
        if have_gles and not have_opengl:
            extra_config += (
                # Use the actual GLES context, not an OpenGL one:
                "gl_es 1\n"
                "vid_preferbackend 3\n"
                # This setting greatly improves performance:
                "gles_use_mapped_buffer true\n"
            )

        # A script file with console commands that are always ran when a game starts
        script_file = f"{config_dir}/gzdoom.cfg"
        with open(script_file, "w") as script:
            script.write(
                "# This file is automatically generated by gzdoomGenerator.py\n"
                # In the code, logfile does not appear to be created unless done so explicitly
                f"logfile {batoceraFiles.logdir}gzdoom.log\n"
                f"vid_fps {'true' if system.getOptBoolean('showFPS') else 'false'}\n"
                f"{extra_config}"
                "echo BATOCERA\n"  # easy check that script ran in console
            )
        
        rom_path = os.path.dirname(rom)

        # check the directory name is in the ini file
        if not os.path.exists(ini_file):
            with open(ini_file, "w") as file:
                file.write('[IWADSearch.Directories]\n')
                file.write('Path=/userdata/roms/gzdoom\n')
                file.write('[FileSearch.Directories]\n')
                file.write('Path=/userdata/roms/gzdoom\n')
                file.write('[SoundfontSearch.Directories]\n')
                file.write("Path=" + config_dir + "/soundfonts\n")
                file.write("Path=" + config_dir + "/fm_banks\n")
                file.write('[GlobalSettings]\n')
        else:
            # configparser wasn't working on the default ini file (non-compliant)
            # it's not a true ini file, use this crude method instead
            line_to_add = "Path=" + rom_path +"\n"
            with open(ini_file, "r") as file:
                lines = file.readlines()
                if line_to_add not in lines:
                    for i in range(len(lines)):
                        if lines[i] == "[IWADSearch.Directories]\n":
                            lines.insert(i+1, line_to_add)
                        if lines[i] == "[FileSearch.Directories]\n":
                            lines.insert(i+1, line_to_add)
                
            with open(ini_file, "w") as file:
                file.writelines(lines)
                    
        # also check the config directories are also set
        with open(ini_file, "r") as file:
            lines = file.readlines()
            if fm_banks not in lines:
                for i in range(len(lines)):
                    if lines[i] == "[SoundfontSearch.Directories]\n":
                        lines.insert(i+1, fm_banks)
                
            if sound_fonts not in lines:
                for i in range(len(lines)):
                    if lines[i] == "[SoundfontSearch.Directories]\n":
                        lines.insert(i+1, sound_fonts)
        
        with open(ini_file, "w") as file:
            file.writelines(lines)
               
        if system.isOptSet("gz_joystick") and system.config["gz_joystick"] == "True":
            # Enable the joystick for configuration in GZDoom by the user currently
            with open(ini_file, "r") as file:
                lines = file.readlines()
            # Set a flag to track whether the line was found or not
            joystick_line_found = False
            
            for i, line in enumerate(lines):
                if line.strip() == "use_joystick=false":
                    lines[i] = "use_joystick=true\n"
                    joystick_line_found = True
                    break
                elif line.strip() == "[GlobalSettings]":
                    lines.insert(i + 1, "use_joystick=true\n")
                    joystick_line_found = True
                    break
            
            if not joystick_line_found:
                for i, line in enumerate(lines):
                    if line.strip() == "[GlobalSettings]":
                        lines.insert(i + 1, "use_joystick=true\n")
                        break
            else:
                lines.append("[GlobalSettings]\n")
                lines.append("use_joystick=true\n")
            
            with open(ini_file, "w") as file:
                file.writelines(lines)
        else:
            # Disable controllers because support is poor
            # we use evmapy instead for now...
            with open(ini_file, "r") as file:
                lines = file.readlines()
            # Set a flag to track whether the line was found or not
            joystick_line_found = False
            
            for i, line in enumerate(lines):
                if line.strip() == "use_joystick=true":
                    lines[i] = "use_joystick=false\n"
                    joystick_line_found = True
                    break
                elif line.strip() == "[GlobalSettings]":
                    lines.insert(i + 1, "use_joystick=false\n")
                    joystick_line_found = True
                    break
            
            if not joystick_line_found:
                for i, line in enumerate(lines):
                    if line.strip() == "[GlobalSettings]":
                        lines.insert(i + 1, "use_joystick=false\n")
                        break
            else:
                lines.append("[GlobalSettings]\n")
                lines.append("use_joystick=false\n")
            
            with open(ini_file, "w") as file:
                file.writelines(lines)
        
        # define how wads are loaded
        # if we use a custom extension use that instead
        if rom.endswith(".gzdoom"):
            with open(rom, "r") as f:
                iwad_command = f.read().strip()
            args = shlex.split(iwad_command)
            return Command.Command(
                array=[
                    "gzdoom",
                    *args,
                    "-exec", script_file,
                    "-width", str(gameResolution["width"]),
                    "-height", str(gameResolution["height"]),
                    "-nologo" if system.getOptBoolean("nologo") else "",
                ]
            )
        else:
            return Command.Command(
                array=[
                    "gzdoom",
                    "-iwad", os.path.basename(rom),
                    "-exec", script_file,
                    "-width", str(gameResolution["width"]),
                    "-height", str(gameResolution["height"]),
                    "-nologo" if system.getOptBoolean("nologo") else "",
                ]
            )
