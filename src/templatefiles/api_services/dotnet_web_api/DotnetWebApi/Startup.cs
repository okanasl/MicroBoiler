﻿


//& region if(authorization)
    //& region if(identityserver4)
using IdentityServer4.AccessTokenValidation;
    //& endregion
    //& region if(keycloack)
    // TODO: Implement keycloack
    //& endregion
//& endregion

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.HttpsPolicy;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;
using DotnetWebApi.Services;
using DotnetWebApi.Data;
using Microsoft.EntityFrameworkCore;
//& region (server)
using Microsoft.AspNetCore.HttpOverrides;
//& endregion (server)
//& region (eventbus)
using MassTransit;
using MassTransit.ExtensionsDependencyInjectionIntegration;
//& endregion (eventbus)

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
            
//& region (database)
            string connectionString = "{{database:connectionString}}";
    //& region (mssql)
            services.AddDbContext<NameContext>(options =>
                options.UseSqlServer(connectionString)
                );
    //& endregion (mssql)
    //& region (mysql)
            services.AddDbContext<NameContext>(options =>
                options.UseMySql(connectionString)
                );
    //& endregion (mysql)
    //& region (postgresql)
            services.AddDbContext<NameContext>(options =>
                options.UseNpgsql(connectionString)
                );
    //& endregion (postgresql)
//& endregion (database)
//& region (cache)
    //& region (redis)
            services.AddDistributedRedisCache(option =>
            {
                option.Configuration = "{{redis_options:connection}}";
                option.InstanceName = "{{redis_options:instance_name}}";
            });
    //& endregion (redis)
    //& region (memory)
            services.AddMemoryCache(options => {
                // Your options
            });            
    //& endregion (memory)
//& endregion (cache)
//& region (authorization)
            // Use In your controller like
            // [Authorize(Policy = "Your_Authorization")]
            services.AddAuthorization(options =>
            {
                options.AddPolicy("Your_Authorization", policyUser =>
                {
                    // You may want change below
                    // policyUser.RequireRole("fso.api.user");
                });
            });
    //& region (identityserver4)
            services.AddAuthentication(IdentityServerAuthenticationDefaults.AuthenticationScheme)
               .AddIdentityServerAuthentication(options =>
               {
                   options.Authority = "{{authorization:authority}}";
                   options.ApiName = "{{authorization:api_name}}";
                   options.ApiSecret = "{{authorization:api_secret}}";
                   options.RequireHttpsMetadata = false;
                   options.SupportedTokens = SupportedTokens.Both;
               });
    //& endregion identityserver4
//& endregion
//& region (eventbus)
    //& region (eventbus:rabbitmq)
            services.AddMassTransit(p=>{
                // p.AddConsumer<AnEventHappenedConsumer>();
            });
            services.AddSingleton(provider => Bus.Factory.CreateUsingRabbitMq(cfg =>
            {
                var host = cfg.Host("localhost", "/", h => {
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
    //& endregion (eventbus:rabbitmq)
//& endregion (eventbus)
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
        }

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(
            IApplicationBuilder app,
            IHostingEnvironment env
//& region (logging)
            ,ILoggerFactory loggerFactory
//& endregion (logging)
        )
        {
//& region (logging)
            loggerFactory.AddConsole(Configuration.GetSection("Logging"));
            loggerFactory.AddDebug();            
//& endregion (logging)
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
            }
            else
            {
                app.UseHsts();
            }
//& region (authorization)
            app.UseAuthentication();
//& endregion (authorization)
//& region (server)
            app.UseForwardedHeaders(new ForwardedHeadersOptions
            {
                ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto
            });
//& endregion (server)
            app.UseCors("CorsPolicy");
            // app.UseHttpsRedirection(); After you configure with nginx
            app.UseMvc();
        }
    }
}
