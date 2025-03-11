"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr

class ConstMap(gr.sync_block):
    """
    Map 0, 1 to -1, 1
    """
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='Bit -> Symbol Map',
            in_sig=[np.float32],
            out_sig=[np.float32]
        )

    def work(self, input_items, output_items):
        """
        map
        """
        sym_map = {0.0: -1.0, 1.0: 1.0, 2.0: 0.0}
        output_items[0][:] = [sym_map[x] for x in input_items[0]]
        return len(output_items[0])
