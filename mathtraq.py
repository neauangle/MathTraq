import sys
import equation
import random
import os
import re
import mpmath
import audio
import shutil
import localutil
import equationtemplate
import arghandler
import json



class mathtraq():
    def __init__(self):
        """
        Apart from initialising this, creates the doomed temp folder
        """
        self.equations = list()
        self.temp_dir = 'temp'
        self.verbosity = None
        localutil.create_dir_if_absent(self.temp_dir)
        

    def print(self, text, v_level, end='\n'):
        """
        Prints text if v_level is less than or equal to
        self.run_info.verbosity
        """
        if v_level <= self.verbosity:
            print(text, end=end)


    def clean_up(self):
        """
        Cleans up temp files, etc.
        """
        shutil.rmtree(self.temp_dir, ignore_errors=True)


    def get_filename_in_temp(self, filename):
        """
        Returns a path to the filename inside the doomed temp folder
        """
        return os.path.join(self.temp_dir, filename)


    def output_to_mp3(self, audio_filenames, output_file, buffer_size):
        """
        Takes a list of ordered mp3 filenames and concatenates them together
        into output_file. This operation is immutable- the original
        files are safe. I've had buffsize above 800 and it's worked, so feel
        free to play around.
        """
        
        #mp3cat can't have an input file be the output file
        #so we flip-flop between two output files, keeping and
        # renaming the bigger one at the end.  
        temp_name_1 = self.get_filename_in_temp('temp1.mp3')
        temp_name_2 = self.get_filename_in_temp('temp2.mp3')
        with open(temp_name_1, 'w'):
            pass
        with open(temp_name_2, 'w'):
            pass  

        flip = True
        #print some info
        num_batches = int(len(audio_filenames) / buffer_size)
        if not num_batches == len(audio_filenames) / buffer_size:
            num_batches += 1
        self.print("\nMixing " + str(num_batches) + " batches of maximum size " + str(buffer_size), 1)

        #go in buffer-size increments along audio_filenames
        for i in range(0, len(audio_filenames), buffer_size):
            #get buffer chunk
            current_filenames = audio_filenames[i:i+buffer_size]
            #every second time, flip so we're outputting to different temp
            current_output = temp_name_1
            if not i == 0:
                if flip:
                    current_filenames.insert(0, temp_name_1)
                    current_output = temp_name_2
                else:
                    current_filenames.insert(0, temp_name_2)
                    current_output = temp_name_1
                flip = not flip
            audio.create_audio_by_concatenation(current_filenames, current_output, 
                                                silently=self.verbosity <= 2)
            
            #print out progress message
            num_done = i + len(current_filenames)-1
            out_of = len(audio_filenames)
            if i == 0:
                num_done += 1
            self.print("\nMixed: " + str(num_done) + " / " + str(out_of), 2)

        #move the longest temp out of doomed temp folder
        localutil.remove_file_if_exists(output_file)
        if os.path.getsize(temp_name_1) > os.path.getsize(temp_name_2):
            os.rename(temp_name_1, output_file)
        else:
            os.rename(temp_name_2, output_file)


    def generate_equations(self, template, precision):
        """
        returns a list with a number of equations
        that fit the template parameters
        """
        with mpmath.workdps(precision):
            equations = list()
            for i in range(0, template.num_eqs):
                #get a random lhs
                lhs = localutil.get_random(template.lhs_min, template.lhs_max, template.lhs_max_dec)
                #get a random op
                op = random.sample(template.ops, 1)[0]
                #get a random rhs
                rhs = localutil.get_random(template.rhs_min, template.rhs_max, template.rhs_max_dec)
                equations.append(equation.Equation(lhs, op, rhs, precision, template.ms_pause, template.ans_max_dec))
                self.print(equations[-1].full_as_string(), 2)

        return equations


    def main(self, argv):    
        """
        Called on command-line runs. 
        Turns user arguments into equation templates,
        fills them out and creates an audio file for them
        """
        #parse arguments
        run_info = arghandler.generate_run_info(argv)
        self.verbosity = run_info.verbosity

        self.print("\nInput valid. Generating equations...", 1)
        for template in run_info.equation_templates:
            self.equations.extend(self.generate_equations(template, run_info.max_digits))
        random.shuffle(self.equations)

        #output json of all equations if user argued for it
        if run_info.output_json:
            self.print("\nDone. Writing out json...", 1)
            with open(run_info.output_json, 'w') as f:
                f.write(json.dumps([eq.to_dict() for eq in self.equations]))

        
        silence_between_q = self.get_filename_in_temp('between_questions.mp3')
        self.print("\nDone. Compiling audio template...", 1)
        audio_filenames = list()
        for eq in  self.equations:
            audio_filenames.extend(eq.full_as_audio_filenames(self.temp_dir))
            #create temp silence file if needed
            inner_pause_file = eq.get_pause_filename(self.temp_dir)
            if not os.path.isfile(inner_pause_file):
                audio.create_silence_file(eq.ms_pause, inner_pause_file, 
                                          silently=self.verbosity <= 2)
            audio_filenames.append(silence_between_q)
        #silence between questions
        self.print("\nDone. Creating pause file...", 1)
        audio.create_silence_file(run_info.ms_pause, silence_between_q, 
                                silently=self.verbosity <= 2)
        self.print("\nDone. Constructing audio...", 1)
        self.output_to_mp3(audio_filenames, run_info.output_mp3, run_info.buffer_size)
        self.print("\nDone. Cleaning up...", 1)
        self.clean_up()
        self.print("\nDone. Enjoy!\n", 1)




if __name__ == "__main__":
    mt = mathtraq()
    mt.main(sys.argv)


"""
TODO
    * redo sounds and make them slightly robotic by raising the treble and giving an echo with 0.01 delay, ~0.6 decay
    * make proper package
"""
