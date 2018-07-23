#region (build_dev)
FROM microsoft/dotnet:2.1-sdk-alpine AS build
# Set the working directory witin the container
WORKDIR /src

# Copy all of the source files
COPY * .

# Restore all packages
RUN dotnet restore ./src/{{project_name}}.csproj

# Build the source code
RUN dotnet build ./src/{{project_name}}.csproj

# Ensure that we generate and migrate the database
RUN chmod +x migrations.sh
RUN chmod +x updatedb.sh
RUN sh migrations.sh
RUN sh updatedb.sh

# Publish application
WORKDIR ..
RUN dotnet publish ./src/{{project_name}}.csproj --output "../../dist"

# Build runtime image
FROM microsoft/dotnet:2.1-aspnetcore-runtime-alpine AS app
WORKDIR /app
COPY --from=build /dist .
ENV ASPNETCORE_URLS http://+:{{port}}

ENTRYPOINT ["dotnet", "{{project_name}}.dll"]

#end (build_dev)