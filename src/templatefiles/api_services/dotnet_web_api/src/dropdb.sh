#!/bin/sh
cd src/{{ProjectName}}
dotnet ef database drop -c {{DatabaseContextName}}
cd ../..
