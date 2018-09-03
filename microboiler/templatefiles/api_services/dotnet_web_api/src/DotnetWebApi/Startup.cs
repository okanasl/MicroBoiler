
using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.HttpsPolicy;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

//& region (authorization)
//& region (authorization:identityserver4)
using IdentityServer4.AccessTokenValidation;
//& end (authorization:identityserver4)
//& region (authorization:keycloack)
    // In Future..
//& end (authorization:keycloack)
//& end (authorization)
//& region (logging)
using Microsoft.Extensions.Logging;
//& end (logging)
//& region (eventbus)
using DotnetWebApi.Services;
//& end (evenybus)
//& region (database)
using DotnetWebApi.Data;
//& end (database)
//& region (database)
using Microsoft.EntityFrameworkCore;
//& end (database)
//& region (server)
using Microsoft.AspNetCore.HttpOverrides;
//& end (server)
//& region (eventbus)
using MassTransit;
using MassTransit.ExtensionsDependencyInjectionIntegration;
//& end (eventbus)
//& region (swagger)
using Swashbuckle.AspNetCore.Swagger;
//& end (swagger)
namespace DotnetWebApi
{
    public class Startup
    {
        public Startup(IConfiguration configuration)
        {
            Configuration = configuration;
        }

        public IConfiguration Configuration { get; }

        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            string env = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT");
            //& region (database)
            string connectionString;   
            //& end (database)  
            //& region (cache)
            //& region (cache:redis)
            string redisConnString;
            //& end (cache:redis)
            //& end (cache)
            //& region (authorization)
            string authConnectionIssuerUrl;            
            //& end (authorization)
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
            string rabbitHostString;
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            if (env == "Development")
            {
            //& region (database)
                connectionString= "{{database:connectionString-dev}}";  
            //& end (database)  
            //& region (cache)
            //& region (cache:redis)
                redisConnString = "{{redis_options:connection-dev}}";
            //& end (cache:redis)
            //& end (cache)
            //& region (authorization)
                authConnectionIssuerUrl= "{{authorization:authority-dev}}";
            //& end (authorization)
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
                rabbitHostString = "{{rabbitmq:host-dev}}";
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            }
            else // if (env == "Docker_Production")
            {
            //& region (database)
                connectionString= @"{{database:connectionString}}";  
            //& end (database)  
            //& region (cache)
            //& region (cache:redis)
                redisConnString = "{{redis_options:connection}}";
            //& end (cache:redis)
            //& end (cache)
            //& region (authorization)
                authConnectionIssuerUrl= "{{authorization:authority}}";
            //& end (authorization)
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
                rabbitHostString = "{{rabbitmq:host}}";
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            }
//& region (database)
    //& region (database:mssql)
            services.AddDbContext<NameContext>(options =>
                options.UseSqlServer(connectionString)
                );
    //& end (database:mssql)
    //& region (database:mysql)
            services.AddDbContext<NameContext>(options =>
                options.UseMySql(connectionString)
                );
    //& end (database:mysql)
    //& region (database:postgresql)
            services.AddDbContext<NameContext>(options =>
                options.UseNpgsql(connectionString)
                );
    //& end (database:postgresql)
//& end (database)
//& region (cache)
    //& region (cache:redis)
            services.AddDistributedRedisCache(option =>
            {
                option.Configuration = redisConnString;
                option.InstanceName = "{{redis_options:instance_name}}";
            });
    //& end (cache:redis)
    //& region (cache:memory)
            services.AddMemoryCache(options => {
                // Your options
            });            
    //& end (cache:memory)
//& end (cache)
//& region (authorization)
            services.AddAuthorization(options =>
            {
                // options.AddPolicy("Your_Authorization", policyUser =>
                // {
                //      // You may want change below for your requirements
                //      policyUser.RequireRole("Admin");
                // });
            });
    //& region (authorization:identityserver4)
            services.AddAuthentication(IdentityServerAuthenticationDefaults.AuthenticationScheme)
               .AddIdentityServerAuthentication(options =>
               {
                   options.Authority = authConnectionIssuerUrl;
                   options.ApiName = "{{authorization:api_name}}";
                   options.ApiSecret = "{{authorization:api_secret}}";
                   options.RequireHttpsMetadata = false;
                   options.SupportedTokens = SupportedTokens.Both;
               });
    //& end (authorization:identityserver4)
//& end (authorization)
//& region (eventbus)
    //& region (eventbus:rabbitmq)
            services.AddMassTransit(p=>{
                // p.AddConsumer<AnEventHappenedConsumer>();
            });
            services.AddSingleton(provider => Bus.Factory.CreateUsingRabbitMq(cfg =>
            {
                var host = cfg.Host(new Uri(rabbitHostString), "/", h => {
                    h.Username("{{rabbitmq:user:username}}");
                    h.Password("{{rabbitmq:user:password}}");
                });

                cfg.ReceiveEndpoint(host, e =>
                {
                    e.PrefetchCount = 8;
                    // Add Event Consumers Here Like:
                    // e.Consumer<AnEventHappenedConsumer>();
                    // If you want Inject Services in Consumer add provider parameter like below.
                    // e.Consumer<AnEventHappenedConsumer>(provider);
                });
            }));
            services.AddSingleton<IPublishEndpoint>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<ISendEndpointProvider>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<IBus>(provider => provider.GetRequiredService<IBusControl>());
            // Register with IHostedService To Start bus when Application Starts and Stop when Application Stops
            // Then you can Inject IBus to publish your messages
            services.AddSingleton<Microsoft.Extensions.Hosting.IHostedService, BusService>();        
    //& end (eventbus:rabbitmq)
//& end (eventbus)
            // You may want to change allowed origins for security.
            services.AddCors(options =>
            {
                options.AddPolicy("CorsPolicy",
                    builder => builder
                    .AllowAnyOrigin()                   
                    .AllowAnyMethod()
                    .AllowAnyHeader()
                    .AllowCredentials()
                    .Build());
            });
            services
                .AddMvc()
                .AddJsonOptions(options =>
                {
                    options.SerializerSettings.ContractResolver = new CamelCasePropertyNamesContractResolver();
                    options.SerializerSettings.ReferenceLoopHandling = ReferenceLoopHandling.Ignore;
                })
                .SetCompatibilityVersion(CompatibilityVersion.Version_2_1);
//& region (swagger)
            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new Info { Title = "My API", Version = "v1" });
            });
//& end (swagger)
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(
            IApplicationBuilder app,
            IHostingEnvironment env
//& region (logging)
            ,ILoggerFactory loggerFactory
//& end (logging)
        )
        {
//& region (logging)
            loggerFactory.AddConsole(Configuration.GetSection("Logging"));
            loggerFactory.AddDebug();            
//& end (logging)
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }
            else
            {
                // app.UseHsts(); After you configure SSL with nginx
            }
//& region (authorization)
            app.UseAuthentication();
//& end (authorization)
//& region (server)
            app.UseForwardedHeaders(new ForwardedHeadersOptions
            {
                ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto
            });
//& end (server)
            app.UseCors("CorsPolicy");
//& region (swagger)
            app.UseSwagger();
            // Enable middleware to serve swagger-ui (HTML, JS, CSS, etc.), 
            // specifying the Swagger JSON endpoint.
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/swagger/v1/swagger.json", "My API V1");
            });
//& end (swagger)
            // app.UseHttpsRedirection(); After you configure SSL with nginx
            app.UseMvc();
        }
    }
}
