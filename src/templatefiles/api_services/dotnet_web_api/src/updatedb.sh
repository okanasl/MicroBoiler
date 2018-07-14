#!/usr/bin/bash
cd src/{{ProjectName}}
dotnet ef database update -c {{DatabaseContextName}}
cd ../..
