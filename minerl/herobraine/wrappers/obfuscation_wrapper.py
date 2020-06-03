import numpy as np
from collections import OrderedDict

from minerl.herobraine.hero import spaces
from minerl.herobraine.wrappers.vector_wrapper import Vectorized
from minerl.herobraine.wrapper import EnvWrapper
import copy
import dill
import os

# TODO: Force obfuscator nets to use these.
SIZE_FILE_NAME = 'size'
ACTION_OBFUSCATOR_FILE_NAME = 'action.secret.compat'
OBSERVATION_OBFUSCATOR_FILE_NAME = 'obs.secret.compat'

class Obfuscated(EnvWrapper):

    def __init__(self, env_to_wrap: Vectorized, obfuscator_dir, name=''):
        """The obfuscation class.

        Args:
            env_to_wrap (Vectorized): The vectorized environment to wrap.
            obfuscator_dir (str, os.path.Path): The path to the obfuscator neural networks.
            name (str, optional): A method to overide the name. Defaults to ''.
        """
        self.obf_vector_len, \
            self.ac_enc, self.ac_dec, \
            self.obs_enc, self.obs_dec = Obfuscated._get_obfuscator(obfuscator_dir)

        super().__init__(env_to_wrap)

        # TODO load these from file
        assert isinstance(env_to_wrap, Vectorized), 'Obfuscated env wrappers only supported for vectorized environments'

        # Compute the no op vertors
        self.observation_no_op = self.env_to_wrap.wrap_observation(self.env_to_wrap.env_to_wrap.observation_space.no_op())['vector']
        self.action_no_op = self.env_to_wrap.wrap_action(self.env_to_wrap.env_to_wrap.action_space.no_op())['vector']

        if name:
            self.name = name
    
    @staticmethod
    def _get_obfuscator(obfuscator_dir : Union[str, os.path.Path]):
        """Gets the obfuscator from a directory.

        Args:
            obfuscator_dir (Union[str, os.path.Path]): The directory containg the pickled obfuscators.
        """
        # TODO: This code should be centralized with the make_obfuscator network.
        assert os.path.exists(obfuscator_dir), f"{obfuscator_dir} not found."
        assert os.listdir(obfuscator_dir) == {SIZE_FILE_NAME, ACTION_OBFUSCATOR_FILE_NAME, OBSERVATION_OBFUSCATOR_FILE_NAME}

        # TODO: store size within the pdill.
        with open(os.path.join(obfuscator_dir), 'r') as f:
            obf_vector_len = int(f.read())

        
        # Get the directory for the actions
        with open(os.path.join(obfuscator_dir, 'action.secret.compat'), 'rb') as f:
            ac_enc, ac_dec = dill.load(f)

        with open(os.path.join(obfuscator_dir, 'obs.secret.compat', 'rb')) as f:
            obs_enc, obs_dec = dill.load(f)

        return obf_vector_len, ac_enc, ac_dec,  obs_enc, obs_dec

        

    def _update_name(self, name: str) -> str:
        return name.split('-')[0] + 'Obf-' + name.split('-')[-1]

    def create_observation_space(self):
        obs_space = copy.deepcopy(self.env_to_wrap.observation_space)
        # TODO: Properly compute the maximum
        obs_space.spaces['vector'] = spaces.Box(low=-1.05, high=1.05, shape=[self.obf_vector_len])
        return obs_space

    def create_action_space(self):
        act_space = copy.deepcopy(self.env_to_wrap.action_space)
        act_space.spaces['vector'] = spaces.Box(low=-1.05, high=1.05, shape=[self.obf_vector_len])
        return act_space

    def _wrap_observation(self, obs: OrderedDict) -> OrderedDict:
        obs['vector'] = self.obs_enc(obs['vector'])
        return obs

    def _wrap_action(self, act: OrderedDict) -> OrderedDict:
        act['vector'] = self.ac_enc(act['vector'])
        return act

    def _unwrap_observation(self, obs: OrderedDict) -> OrderedDict:
        obs['vector'] = np.clip(self.obs_dec(obs['vector']),0,1)
        return obs

    def _unwrap_action(self, act: OrderedDict) -> OrderedDict:
        act['vector'] = np.clip(self.ac_dec(act['vector']),0,1)
        return act

    def get_docstring(self):
        # TODO fix this
        return super().get_docstring()
