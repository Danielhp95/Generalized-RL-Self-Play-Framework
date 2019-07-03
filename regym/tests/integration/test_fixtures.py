import pytest
from regym.environments import parse_environment


@pytest.fixture
def ppo_config_dict():
    config = dict()
    config['discount'] = 0.99
    config['use_gae'] = False
    config['use_cuda'] = False
    config['gae_tau'] = 0.95
    config['entropy_weight'] = 0.01
    config['gradient_clip'] = 5
    config['optimization_epochs'] = 10
    config['mini_batch_size'] = 256
    config['ppo_ratio_clip'] = 0.2
    config['learning_rate'] = 3.0e-4
    config['adam_eps'] = 1.0e-5
    config['horizon'] = 1024
    config['phi_arch'] = 'MLP'
    config['actor_arch'] = 'None'
    config['critic_arch'] = 'None'
    return config


@pytest.fixture
def i2a_config_dict():
    config = dict()
    config['observation_resize_dim'] = 80
    config['rollout_length'] = 5
    config['reward_size'] = 1
    config['imagined_rollouts_per_step'] = 3
    config['environment_update_horizon'] = 1
    config['policies_update_horizon'] = 1
    config['environment_model_learning_rate'] = 1.0e-3
    config['environment_model_adam_eps'] = 1.0e-5
    config['policies_learning_rate'] = 1.0e-3
    config['policies_adam_eps'] = 1.0e-5
    config['preprocess_function'] = 'ResizeCNNPreprocessFunction'
    config['use_cuda'] = False
    # Environment Model: Architecture description:
    config['environment_model_arch'] = 'CNN'
    config['environment_model_channels'] = [32]
    # Rollout Encoder:
    config['rollout_encoder_channels'] = [32, 32, 32]
    config['rollout_encoder_kernels'] = [3, 3, 3]
    config['rollout_encoder_strides'] = [1, 1, 1]
    config['rollout_encoder_paddings'] = [0, 0, 0]
    config['rollout_encoder_feature_dim'] = 512
    config['rollout_encoder_nbr_hidden_units'] = (256,)
    config['rollout_encoder_embedding_size'] = 256
    # Distilled Policy: Convolutional architecture description
    config['distill_policy_arch'] = 'CNN'
    config['distill_policy_channels'] = [32, 64, 128]
    config['distill_policy_kernels'] = [8, 4, 3]
    config['distill_policy_strides'] = [4, 3, 1]
    config['distill_policy_paddings'] = [0, 0, 0]
    config['distill_policy_feature_dim'] = 512
    # Distilled Policy: Fully Connected architecture description
    config['distill_policy_nbr_hidden_units'] = None
    # Distilled Policy: Head architecture description
    config['distill_policy_head_arch'] = 'MLP'
    config['distill_policy_head_nbr_hidden_units'] = (256, 128)

    # Model Free Path: Convolutional architecture description
    config['model_free_network_arch'] = 'CNN'
    config['model_free_network_channels'] = [32, 32, 64]
    config['model_free_network_kernels'] = [8, 4, 3]
    config['model_free_network_strides'] = [4, 3, 1]
    config['model_free_network_paddings'] = [0, 0, 0]
    config['model_free_network_feature_dim'] = 512
    # Model Free Path: Fully Connected architecture description
    config['model_free_network_nbr_hidden_units'] = None

    config['actor_critic_head_actor_arch'] = 'MLP'
    config['actor_critic_head_actor_nbr_hidden_units'] = (128,)
    config['actor_critic_head_critic_arch'] = 'MLP'
    config['actor_critic_head_critic_nbr_hidden_units'] = (128,)
    return config


@pytest.fixture
def otc_task():
    import os
    here = os.path.abspath(os.path.dirname(__file__))
    return parse_environment(os.path.join(here, 'ObstacleTower/obstacletower'))
