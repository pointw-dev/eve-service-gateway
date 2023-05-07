@echo off
setlocal

echo About to delete all images containing the string "eve-service-gateway"
SET /P AREYOUSURE=Are you sure (Y/[N])?
IF /I "%AREYOUSURE%" NEQ "Y" GOTO END

for /F %%i in ('docker image ls --format "{{.Repository}}:{{.Tag}}" --filter "reference=eve-service-gateway"') do docker image rm %%i -f

:end
endlocal
