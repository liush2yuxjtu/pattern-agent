"""Readable executed conditions; preserve the original input without mutation."""
from copy import deepcopy


def readable_conditions(source):
    result = deepcopy(source['config'])
    features = source['solver_features']
    result['实际启用的求解功能'] = {
        '人体表面采样接触': bool(features.get('surface_contacts')),
        '人体真实三角面特征接触': bool(features.get('body_feature_contacts')),
        '布料点面与边边接触': bool(features.get('self_contacts')),
        '离散自交状态保护': bool(features.get('self_step_guard')),
        '实际准备迭代数': features.get('placement_relaxation_iterations', 0),
        '保护边界': '逐阶段检查实际float32位置；不代表两帧之间连续无碰撞或实测材料批准',
    }
    return result
