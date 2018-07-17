using System;
using System.Linq;
using System.Security.Claims;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Rendering;
using Microsoft.Extensions.Logging;
using IdentityServer4.Services;
using IdentityServer4.Stores;
using IdentityServer4.Models;
using IdentityModel;
using IdentityServer4;
using IdentityServer4.Extensions;
using System.Globalization;
using Host.Models;
using Host.Services;
using IdentityServer4.Entities;

namespace Host.Controllers
{
    [SecurityHeaders]
    [Authorize]
    public class InstallController : Controller
    {
        private readonly UserManager<ApplicationUser> _userManager;
        private readonly RoleManager<ApplicationRole> _roleManager;
        private readonly SignInManager<ApplicationUser> _signInManager;
        private readonly IEmailSender _emailSender;
        private readonly ISmsSender _smsSender;
        private readonly ILogger _logger;
        private readonly IIdentityServerInteractionService _interaction;
        private readonly IClientStore _clientStore;
        private readonly ClientSelector _clientSelector;
        private readonly IPersistedGrantService _persistedGrantService;

        public InstallController(
            UserManager<ApplicationUser> userManager,
            RoleManager<ApplicationRole> roleManager,
            IPersistedGrantService persistedGrantService,
            SignInManager<ApplicationUser> signInManager,
            IEmailSender emailSender,
            ISmsSender smsSender,
            ILoggerFactory loggerFactory,
            IIdentityServerInteractionService interaction,
            IClientStore clientStore,
            ClientSelector clientSelector)
        {
            _userManager = userManager;
            _roleManager = roleManager;
            _persistedGrantService = persistedGrantService;
            _signInManager = signInManager;
            _emailSender = emailSender;
            _smsSender = smsSender;
            _logger = loggerFactory.CreateLogger<AccountController>();
            _interaction = interaction;
            _clientStore = clientStore;
            _clientSelector = clientSelector;
        }

        //
        // GET: /Install
        [HttpGet]
        [AllowAnonymous]
        public async Task<IActionResult> Index()
        {
            var users = await _userManager.GetUsersInRoleAsync("UI_Admin");
            // TODO: Uncomment if clause
            // if(users.Count > 0){
            //     ModelState.AddModelError(string.Empty, "There is already an Admin Account");
            //     ModelState.AddModelError(string.Empty, "Consider, forget password button");
            // }
            InstallViewModel model = new  InstallViewModel();
            model.Email = "your_secure@email.com";
            model.Username = "admin_username";
            return View(model);
        }

        //
        // POST: /Install
        [HttpPost]
        [AllowAnonymous]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> Index(InstallViewModel model)
        {
            if (ModelState.IsValid)
            {
                ApplicationRole role = new ApplicationRole("UI_Admin")
                {
                    NormalizedName = "UI_Admin".ToUpper()
                };
                if(!await _roleManager.RoleExistsAsync(role.Name))
                {                        
                    await _roleManager.CreateAsync(role);                   
                }
                var user = new ApplicationUser { UserName = model.Username, Email = model.Email };
                var result = await _userManager.CreateAsync(user, model.Password);
                if (result.Succeeded)
                {
                    await _userManager.AddToRoleAsync(user,role.Name);
                    await _signInManager.SignInAsync(user, isPersistent: false);
                    _logger.LogInformation(3, "Admin User Created.");
                    return RedirectToLocal(returnUrl: "Home");
                }
                AddErrors(result);
            }

            // If we got this far, something failed, redisplay form
            return View(model);
        }

        #region Helpers

        private void AddErrors(IdentityResult result)
        {
            foreach (var error in result.Errors)
            {
                ModelState.AddModelError(string.Empty, error.Description);
            }
        }

        private Task<ApplicationUser> GetCurrentUserAsync()
        {
            return _userManager.GetUserAsync(HttpContext.User);
        }

        private IActionResult RedirectToLocal(string returnUrl)
        {
            if (Url.IsLocalUrl(returnUrl))
            {
                return Redirect(returnUrl);
            }
            else
            {
                return RedirectToAction(nameof(IdentityServer4.Quickstart.UI.HomeController.Index), "Home");
            }
        }

        #endregion

    }
}
