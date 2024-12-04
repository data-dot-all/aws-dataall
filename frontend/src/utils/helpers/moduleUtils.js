/* eslint-disable no-restricted-properties */
import * as modules from 'modules';
import config from '../../generated/config.json';

function _resolveModuleName(module) {
  return Object.values(modules).find((_module) => _module.name === module);
}

function _hasDependencyModule(module) {
  const resolvedModule = _resolveModuleName(module);
  return typeof resolvedModule?.resolve_dependency === 'function';
}

function isModuleEnabled(module) {
  if (_hasDependencyModule(module)) {
    const resolvedModule = _resolveModuleName(module);
    return resolvedModule.resolve_dependency();
  }
  return getModuleActiveStatus(module);
}

function getModuleActiveStatus(moduleKey) {
  if (
    config.modules &&
    config.modules[moduleKey] &&
    config.modules[moduleKey].active !== undefined
  ) {
    return config.modules[moduleKey].active;
  }
  return false;
}

function isFeatureEnabled(moduleKey, featureKey) {
  if (
    moduleKey === 'core' &&
    config.core.features !== undefined &&
    config.core.features[featureKey] !== undefined
  ) {
    return config.core.features[featureKey];
  } else if (
    getModuleActiveStatus(moduleKey) &&
    config.modules[moduleKey]['features'] !== undefined &&
    config.modules[moduleKey]['features'][featureKey] !== undefined
  ) {
    if (
      config.modules[moduleKey]['features'][featureKey]['active'] !== undefined
    ) {
      return config.modules[moduleKey]['features'][featureKey]['active'];
    } else {
      return config.modules[moduleKey]['features'][featureKey];
    }
  }
  return false;
}

function isAnyEnvironmentModuleEnabled() {
  const env_modules = Object.values(modules).filter(
    (_module) =>
      _module.isEnvironmentModule === true && isModuleEnabled(_module.name)
  );
  return env_modules.length > 0 ? true : false;
}

function _modulesNameMap() {
  const map = {};
  for (const module of Object.values(modules).filter(
    (_module) => _module.moduleDefinition === true
  )) {
    const upperCaseModule = module.name.toUpperCase();
    map[upperCaseModule] = module.name;
  }
  return map;
}

const ModuleNames = _modulesNameMap();
export {
  ModuleNames,
  isModuleEnabled,
  getModuleActiveStatus,
  isFeatureEnabled,
  isAnyEnvironmentModuleEnabled
};
