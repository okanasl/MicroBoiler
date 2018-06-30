#region if (build_dev)
FROM microsoft/dotnet:2.1-sdk-alpine AS build
# Set the working directory witin the container
WORKDIR /src

# Copy all of the source files
COPY * .

# Restore all packages
RUN dotnet restore ./{{proj_name}}/{{proj_name}}.csproj

# Build the source code
RUN dotnet build ./{{proj_name}}/{{proj_name}}.csproj

# Ensure that we generate and migrate the database
RUN dotnet ef database migrate
RUN dotnet ef database update

# Publish application
WORKDIR ..
RUN dotnet publish ./{{proj_name}}/{{proj_name}}.csproj --output "../../dist"

# Build runtime image
FROM microsoft/dotnet:2.1-aspnetcore-runtime-alpine AS app
WORKDIR /app
COPY --from=build /dist .
ENV ASPNETCORE_URLS http://+:{{port}}

ENTRYPOINT ["dotnet", "{{proj_name}}.dll"]

#endregion
#region if (build_container)

FROM microsoft/dotnet:2.1-runtime
COPY ./publish /app
WORKDIR /app
ENV ASPNETCORE_URLS http://+:{{port}}
ENTRYPOINT ["dotnet", "{{proj_name}}.dll"]

#endregion