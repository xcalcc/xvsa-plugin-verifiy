package io.xc5.plugin.verifier;

import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.core.LoggerContext;
import org.apache.logging.log4j.core.config.Configuration;
import org.apache.logging.log4j.core.config.Configurator;
import org.apache.logging.log4j.core.config.LoggerConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

public class Utils {
  private static Logger logger = LoggerFactory.getLogger(Utils.class);

  static List<String> readListFromFile(String fileName) {
    if (!new File(fileName).exists()) {
      throw new VerifyException("File not exist : " + fileName);
    }
    Scanner s = null;
    try {
      s = new Scanner(new File(fileName));
      ArrayList<String> list = new ArrayList<String>();
      boolean firstLine = true;
      while (s.hasNextLine()) {
        String t = s.nextLine();
        if (firstLine) {
          t = t.replaceAll("libraries=", "");
          firstLine = false;
        }
        if (t.trim().length() != 0) {
          list.add(t.trim());
        }
      }
      s.close();
      return list;
    } catch (IOException e) {
      e.printStackTrace();
      throw new VerifyException("Cannot read from list file : " + fileName);
    }
  }

  public static List<String> readListFromFileWithSeparator(String absolutePath, String separator) {
    String s = String.join("", readListFromFile(absolutePath));
    s = s.replaceFirst("libraries=", "");
    return Arrays.stream(s.split(separator)).filter(x -> x.trim().length() > 0).collect(Collectors.toList());
  }

  public static void readPrefixedList(File file, Map<String, List<String>> vtables, List<String> classNames) {
    if (!file.exists()) {
      throw new VerifyException("File not exist : " + file.getAbsolutePath());
    }
    Scanner s = null;
    try {
      s = new Scanner(file);
      ArrayList<String> list = new ArrayList<String>();
      String previousZtv = null;
      List<String> previousVtableContent = null;
      while (s.hasNextLine()) {
        String t = s.nextLine();
        if (t.trim().length() == 0) {
          continue;
        } else if (t.startsWith("_ZTV") || t.startsWith("\t_ZTV")) {
          if (!(previousZtv == null)) {
            vtables.put(previousZtv, previousVtableContent);
          }
          previousZtv = t;
          previousVtableContent = new ArrayList<>();
        } else if (t.startsWith(" ") || t.startsWith("\t")) {
          String v = t.substring(1);
          previousVtableContent.add(v);
        } else if (t.startsWith(":")) {
          classNames.add(t.substring(2));
        }
      }
      s.close();
      if (previousZtv != null) {
        vtables.put(previousZtv, previousVtableContent);
      }
    } catch (IOException e) {
      e.printStackTrace();
      throw new VerifyException("Cannot read from list file : " + file.getAbsolutePath());
    }
  }

  /***
   * Initialize loggers with logLevel
   */
  public static void initLoggers(boolean verbose, int logLevel) {
    Level levelToSet = Level.WARN;
    if (verbose)
      levelToSet = Level.TRACE;
    switch (logLevel) {
      case 0:
        levelToSet = Level.ALL;
        break;
      case 1:
        levelToSet = Level.TRACE;
        break;
      case 2:
        levelToSet = Level.DEBUG;
        break;
      case 3:
        levelToSet = Level.INFO;
        break;
      case 4:
        levelToSet = Level.WARN;
        break;
      case 5:
        levelToSet = Level.ERROR;
        break;
      case 6:
        levelToSet = Level.FATAL;
      default:
        // fall through expected
    }
    LoggerContext ctx = (LoggerContext) LogManager.getContext(false);
    Configuration config = ctx.getConfiguration();
    LoggerConfig loggerConfig = config.getLoggerConfig(LogManager.ROOT_LOGGER_NAME);
    loggerConfig.setLevel(levelToSet);
    ctx.updateLoggers();  // This causes all Loggers to refetch information from their LoggerConfig.
    // org.apache.logging.log4j.core.config.Configurator;
    Configurator.setLevel("io.xc5", levelToSet);
    // You can also set the root logger:
    Configurator.setRootLevel(levelToSet);
    logger.debug("Log level set to : {}", levelToSet);
  }
}
