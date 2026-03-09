@REM ----------------------------------------------------------------------------
@REM Licensed to the Apache Software Foundation (ASF) under one
@REM or more contributor license agreements.  See the NOTICE file
@REM distributed with this work for additional information
@REM regarding copyright ownership.  The ASF licenses this file
@REM to you under the Apache License, Version 2.0 (the
@REM "License"); you may not use this file except in compliance
@REM with the License.  You may obtain a copy of the License at
@REM
@REM    https://www.apache.org/licenses/LICENSE-2.0
@REM
@REM Unless required by applicable law or agreed to in writing,
@REM software distributed under the License is distributed on an
@REM "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
@REM KIND, either express or implied.  See the License for the
@REM specific language governing permissions and limitations
@REM under the License.
@REM ----------------------------------------------------------------------------

@REM ----------------------------------------------------------------------------
@REM Apache Maven Wrapper startup batch script, version 3.3.4
@REM ----------------------------------------------------------------------------

@IF "%__MVNW_ARG0_NAME__%"=="" (SET "BASE_DIR=%~dp0") ELSE (SET "BASE_DIR=%__MVNW_ARG0_NAME__%")
@SET WRAPPER_PROPERTIES=%BASE_DIR%.mvn\wrapper\maven-wrapper.properties

@IF NOT EXIST "%WRAPPER_PROPERTIES%" (
  ECHO Error: %WRAPPER_PROPERTIES% not found.
  EXIT /B 1
)

@FOR /F "usebackq tokens=1,* delims==" %%A IN ("%WRAPPER_PROPERTIES%") DO (
  IF "%%A"=="distributionUrl" SET "DISTRIBUTION_URL=%%B"
)

@IF "%DISTRIBUTION_URL%"=="" (
  ECHO Error: distributionUrl not found in %WRAPPER_PROPERTIES%
  EXIT /B 1
)

@SET "MAVEN_USER_HOME=%USERPROFILE%\.m2"
@SET "MAVEN_DIST_DIR=%MAVEN_USER_HOME%\wrapper\dists"

@FOR %%F IN ("%DISTRIBUTION_URL%") DO SET "DIST_FILENAME=%%~nxF"
@SET "DIST_NAME=%DIST_FILENAME:-bin.zip=%"
@SET "MAVEN_HOME_LOCAL=%MAVEN_DIST_DIR%\%DIST_NAME%"

@IF NOT EXIST "%MAVEN_HOME_LOCAL%\bin\mvn.cmd" (
  ECHO Downloading Maven from: %DISTRIBUTION_URL%
  IF NOT EXIST "%MAVEN_DIST_DIR%" MKDIR "%MAVEN_DIST_DIR%"
  powershell -Command "Invoke-WebRequest -Uri '%DISTRIBUTION_URL%' -OutFile '%MAVEN_DIST_DIR%\%DIST_FILENAME%'"
  powershell -Command "Expand-Archive -Path '%MAVEN_DIST_DIR%\%DIST_FILENAME%' -DestinationPath '%MAVEN_DIST_DIR%' -Force"
  DEL "%MAVEN_DIST_DIR%\%DIST_FILENAME%"
)

@SET "MVN_CMD=%MAVEN_HOME_LOCAL%\bin\mvn.cmd"
@IF NOT EXIST "%MVN_CMD%" (
  ECHO Error: mvn.cmd not found at %MVN_CMD%
  EXIT /B 1
)

@"%MVN_CMD%" %*
