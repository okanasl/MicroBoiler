#!/bin/sh
cd src
dotnet ef database update -c {{DatabaseContextName}}
cd ..
