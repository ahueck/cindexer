/*---------------------------------------------------------------------------------------------
 *  Copyright (c) Microsoft Corporation. All rights reserved.
 *  Licensed under the MIT License. See LICENSE in the project root for license
 * information.
 *--------------------------------------------------------------------------------------------*/
'use strict';

import * as vscode from 'vscode';

/**
 * API version information.
 */
export enum Version {
  v1 = 1,  // 1.x.x
  v2 = 2,  // 2.x.x
  v3 = 3,  // 3.x.x
  v4 = 4,  // 4.x.x
  v5 = 5,  // 5.x.x
  latest = v5,
}

/**
 * The interface provided by the CMake Tools extension during activation.
 */
export interface CMakeToolsExtensionExports {
  /**
   * Get an API object.
   * @param version The desired API version.
   * @returns The CMake Tools API object for the specified version.
   */
  getApi(version: Version): CMakeToolsApi;
}

/**
 * An interface to allow VS Code extensions to interact with the CMake Tools
 * extension.
 */
export interface CMakeToolsApi {
  readonly version: Version;

  /**
   * Gets the project associated with the given file or folder, if it exists.
   * @param path The file or folder to get the project for.
   * @returns A promise that resolves to the project if it exists, or undefined
   *     otherwise.
   */
  getProject(path: vscode.Uri): Promise<Project|undefined>;

  /**
   * Events related to build and launch targets.
   */
  readonly onBuildTargetChanged: vscode.Event<string>;
  readonly onLaunchTargetChanged: vscode.Event<string>;
  readonly onActiveProjectChanged: vscode.Event<vscode.Uri|undefined>;
}

export interface Project {
  /**
   * Gets the directory where build output is placed, if it is defined.
   * @returns A promise that resolves to the build directory path, or undefined
   *     if not defined.
   */
  getBuildDirectory(): Promise<string|undefined>;
}

/**
 * Helper function to get the CMakeToolsApi from the CMake Tools extension.
 * @param desiredVersion The desired API version.
 * @param exactMatch If true, the version must match exactly.
 * @returns The API object, or undefined if the API is not available.
 */
export async function getCMakeToolsApi(
    desiredVersion: Version,
    exactMatch = false): Promise<CMakeToolsApi|undefined> {
  const extension = vscode.extensions.getExtension('ms-vscode.cmake-tools');

  if (!extension) {
    return undefined;
  }

  let exports: CMakeToolsExtensionExports|undefined;
  if (!extension.isActive) {
    try {
      exports = await extension.activate();
    } catch {
      return undefined;
    }
  } else {
    exports = extension.exports;
  }

  if (!exports || !exports.getApi) {
    return undefined;
  }

  const api = exports.getApi(desiredVersion);
  if (exactMatch && desiredVersion !== api.version) {
    return undefined;
  }

  return api;
}
